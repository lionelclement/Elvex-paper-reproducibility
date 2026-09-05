#!/usr/bin/env python3
"""Run the lexical-context FULL / NO-CONTEXT / PRE-SPECIFIED ablation."""
from __future__ import annotations

import argparse
import csv
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONDITIONS = {
    "FULL": HERE / "full.rules",
    "NO-CONTEXT": HERE / "no-context.rules",
    "PRE-SPECIFIED": HERE / "pre-specified.rules",
}
ARG_SURFACE = {
    "human": "Mary",
    "entity": "the proposal",
    "event": "the meeting",
    "institution": "the company",
    "location": "the city",
}
ARG_LEXICON = {
    "entity": ("proposal", "PROPOSAL"),
    "event": ("meeting", "MEETING"),
    "institution": ("company", "COMPANY"),
    "location": ("city", "CITY"),
}


def load_cases(path: Path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def atom(word: str) -> str:
    return f"_{word}_"


def write_lexicon(path: Path, cases, *, no_context: bool = False):
    supports = {}
    nouns = {}
    for row in cases:
        supports[row["support"]] = row
        nouns[row["predicate"]] = row

    lines = [
        '"." dot [];',
        '',
        'John proper_noun [HEAD:JOHN];',
        '',
        'a det [HEAD:A];',
        '',
    ]

    # Inflected support forms are stored directly: morphology is deliberately
    # outside this ablation. FULL/PRE-SPECIFIED use HEAD lookup. NO-CONTEXT uses
    # a dedicated terminal with HEAD deliberately absent, so Elvex retrieves
    # the complete support inventory by terminal name.
    for support, row in sorted(supports.items()):
        terminal = "support_verb" if no_context else "verb"
        entry = [f'{row["verb"]} {terminal} [']
        if not no_context:
            entry.append(f'    HEAD:{support},')
        entry.extend([
            f'    lexical_aspect:{row["support_aspect"]},',
            f'    phase:{row["support_phase"]},',
            f'    stance:{row["support_stance"]},',
            f'    subjectivity:{row["support_subjectivity"]},',
            f'    register:{row["support_register"]}',
            '];',
            '',
        ])
        lines.extend(entry)

    # Lexicalizing the noun produces the complete inherited structure required
    # by the support verb. This mirrors test/paper_support_context/support.lexicon.
    for predicate, row in sorted(nouns.items()):
        lines.extend([
            f'{row["noun"]} noun [',
            f'    HEAD:{predicate},',
            f'    support:[HEAD:{row["support"]}],',
            f'    pred_class:{row["pred_class"]},',
            f'    aktionsart:{row["aktionsart"]},',
            f'    fixedness:{row["fixedness"]}',
            '];',
            '',
        ])

    path.write_text("\n".join(lines), encoding="utf-8")

def resolve_elvex(explicit: str | None) -> str:
    candidates = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    if os.environ.get("ELVEX_BIN"):
        candidates.append(Path(os.environ["ELVEX_BIN"]).expanduser())
    found = shutil.which("elvex")
    if found:
        candidates.append(Path(found))
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    raise SystemExit(
        "cannot find elvex; install Elvex on PATH, pass --elvex, or set ELVEX_BIN"
    )


def inherited(row, condition: str) -> str:
    base = f'T1 [i:[HEAD:JOHN], ii:[HEAD:{row["predicate"]}]'
    if condition == "PRE-SPECIFIED":
        return base + f', support:[HEAD:{row["support"]}]]\n'
    return base + ']\n'

def expected(row) -> str:
    return f'John {row["verb"]} {row["article"]} {row["noun"]} .'

def normalize_surface(text: str) -> str:
    return ' '.join(text.replace('.', ' . ').split())


def parse_surface(stdout: str):
    out = []
    metric_lines = []
    for raw in stdout.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("ELVEX_METRICS"):
            metric_lines.append(line)
            continue
        out.append(line)
    return out, metric_lines


def parse_metrics(lines: list[str]) -> dict[str, str]:
    """Return the last complete ELVEX_METRICS record, when available."""
    header = None
    values = None
    for line in lines:
        parts = line.rstrip("\n").split("\t")
        if parts and parts[0] == "ELVEX_METRICS_HEADER":
            header = parts[1:]
        elif parts and parts[0] == "ELVEX_METRICS":
            values = parts[1:]
    if header and values and len(header) == len(values):
        return dict(zip(header, values))
    return {}


def run_one(
    elvex: str,
    rules: Path,
    lexicon: Path,
    request: str,
    workdir: Path,
    *,
    max_items: int | None = None,
    metric_id: str | None = None,
):
    input_file = workdir / "request.input"
    input_file.write_text(request, encoding="utf-8")
    cmd = [
        elvex,
    ]
    if max_items is not None:
        cmd.extend(["--max-items", str(max_items)])
    cmd.extend([
        "--rules-file", str(rules),
        "--lexicon-file", str(lexicon),
        "--input-file", str(input_file),
    ])
    env = os.environ.copy()
    env.setdefault("ELVEX_METRICS", "1")
    if metric_id:
        env["ELVEX_METRIC_ID"] = metric_id
    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    wall_ms = (time.perf_counter() - t0) * 1000.0
    if proc.returncode != 0:
        raise RuntimeError(
            f"Elvex failed ({proc.returncode})\ncommand: {' '.join(cmd)}\n"
            f"stdin: {request}\nstderr:\n{proc.stderr}\nstdout:\n{proc.stdout}"
        )
    surfaces, metrics = parse_surface(proc.stdout)
    # Some builds write metrics to stderr.
    _stderr_text, stderr_metrics = parse_surface(proc.stderr)
    metrics.extend(stderr_metrics)
    diagnostics = "\n".join(
        line for line in proc.stderr.splitlines()
        if line.strip() and not line.startswith("ELVEX_METRICS")
    )
    return surfaces, metrics, wall_ms, diagnostics


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--elvex", help="path to the elvex executable")
    ap.add_argument("--cases", type=Path, default=HERE / "cases.tsv")
    ap.add_argument("--output", type=Path, default=HERE / "results.tsv")
    ap.add_argument("--limit", type=int, default=0, help="run only the first N cases")
    ap.add_argument(
        "--conditions",
        default="FULL,NO-CONTEXT,PRE-SPECIFIED",
        help="comma-separated subset of FULL,NO-CONTEXT,PRE-SPECIFIED",
    )
    args = ap.parse_args()

    elvex = resolve_elvex(args.elvex)
    all_cases = load_cases(args.cases)
    cases = all_cases[: args.limit] if args.limit else all_cases
    conditions = [x.strip() for x in args.conditions.split(",") if x.strip()]
    unknown = [x for x in conditions if x not in CONDITIONS]
    if unknown:
        raise SystemExit(f"unknown conditions: {', '.join(unknown)}")

    result_fields = [
        "condition", "case_id", "predicate", "expected", "unique_outputs",
        "valid_outputs", "spurious_outputs", "valid_fraction", "wall_ms",
        "metric_lines", "diagnostics",
    ]
    results = []

    with tempfile.TemporaryDirectory(prefix="elvex-lexical-context-") as td:
        context_lexicon = Path(td) / "benchmark-context.lexicon"
        no_context_lexicon = Path(td) / "benchmark-no-context.lexicon"
        # --limit is an evaluation convenience only. Keep the lexical
        # inventory fixed so all conditions use the same nine support forms.
        # Only the lookup representation differs: HEAD-indexed for FULL/PRE,
        # terminal-indexed (no HEAD) for NO-CONTEXT.
        write_lexicon(context_lexicon, all_cases)
        write_lexicon(no_context_lexicon, all_cases, no_context=True)
        for condition in conditions:
            rules = CONDITIONS[condition]
            lexicon = no_context_lexicon if condition == "NO-CONTEXT" else context_lexicon
            for row in cases:
                surfaces, metric_lines, wall_ms, diagnostics = run_one(
                    elvex, rules, lexicon, inherited(row, condition), Path(td)
                )
                unique = sorted(set(surfaces))
                gold = expected(row)
                norm_unique = {normalize_surface(x) for x in unique}
                valid = int(normalize_surface(gold) in norm_unique)
                spurious = len(unique) - valid
                results.append({
                    "condition": condition,
                    "case_id": row["case_id"],
                    "predicate": row["predicate"],
                    "expected": gold,
                    "unique_outputs": len(unique),
                    "valid_outputs": valid,
                    "spurious_outputs": spurious,
                    "valid_fraction": f"{(valid / len(unique) if unique else 0.0):.8f}",
                    "wall_ms": f"{wall_ms:.3f}",
                    "metric_lines": len(metric_lines),
                    "diagnostics": diagnostics,
                })

    with args.output.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=result_fields, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(results)

    grouped = defaultdict(list)
    for row in results:
        grouped[row["condition"]].append(row)

    print(f"cases: {len(cases)}")
    print("condition\tgenerated\tvalid\tspurious\tvalid_%\twall_ms")
    for condition in conditions:
        rows = grouped[condition]
        generated = sum(int(r["unique_outputs"]) for r in rows)
        valid = sum(int(r["valid_outputs"]) for r in rows)
        spurious = sum(int(r["spurious_outputs"]) for r in rows)
        wall = sum(float(r["wall_ms"]) for r in rows)
        pct = 100.0 * valid / generated if generated else 0.0
        print(f"{condition}\t{generated}\t{valid}\t{spurious}\t{pct:.3f}\t{wall:.3f}")

    failures = [
        r for r in results
        if r["condition"] in {"FULL", "PRE-SPECIFIED"}
        and (int(r["valid_outputs"]) != 1 or int(r["spurious_outputs"]) != 0)
    ]
    if failures:
        print("\nUnexpected FULL/PRE-SPECIFIED results:", file=sys.stderr)
        for r in failures:
            print(
                f'{r["condition"]} {r["case_id"]} {r["predicate"]}: '
                f'valid={r["valid_outputs"]} spurious={r["spurious_outputs"]}',
                file=sys.stderr,
            )
            if r.get("diagnostics"):
                print(f'  diagnostics: {r["diagnostics"][:500]}', file=sys.stderr)
        raise SystemExit(1)
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
