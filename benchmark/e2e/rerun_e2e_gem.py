#!/usr/bin/env python3
"""Prepare and run the E2E/GEM closed-domain realization benchmark."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from collections import OrderedDict
from pathlib import Path
from typing import Any, Iterable

MR_RE = re.compile(r"\s*([A-Za-z][A-Za-z0-9_ ]*)\s*\[([^\]]*)\]\s*")

SLOT_NORMALIZATION = {
    "name": "name",
    "eattype": "eatType",
    "eat type": "eatType",
    "food": "food",
    "pricerange": "priceRange",
    "price range": "priceRange",
    "area": "area",
    "familyfriendly": "familyFriendly",
    "family friendly": "familyFriendly",
    "near": "near",
    "customerrating": "customerRating",
    "customer rating": "customerRating",
    "rating": "customerRating",
}
SUPPORTED_SLOTS = {
    "name", "eatType", "food", "priceRange", "area",
    "familyFriendly", "near", "customerRating",
}


def clean_value(s: Any) -> str:
    s = str(s).replace("_", " ").strip()
    s = re.sub(r"\s+", " ", s)
    if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
        s = s[1:-1].strip()
    return s


def normalize_slot_name(s: str) -> str:
    key = re.sub(r"\s+", " ", s.strip().lower())
    key_no_space = key.replace(" ", "")
    return SLOT_NORMALIZATION.get(
        key,
        SLOT_NORMALIZATION.get(key_no_space, s.strip().replace(" ", "")),
    )


def parse_e2e_mr(mr: Any) -> dict[str, str]:
    if not isinstance(mr, str):
        raise ValueError(f"MR is not a string: {type(mr).__name__}")
    slots: dict[str, str] = {}
    for part in mr.split(","):
        part = part.strip()
        if not part:
            continue
        m = MR_RE.fullmatch(part)
        if not m:
            raise ValueError(f"Cannot parse MR component: {part!r} in MR {mr!r}")
        slot = normalize_slot_name(m.group(1))
        if slot not in SUPPORTED_SLOTS:
            raise ValueError(f"Unsupported slot {slot!r} in MR {mr!r}")
        slots[slot] = clean_value(m.group(2))
    return slots


E2E_SOURCES = {
    "train": {
        "filename": "train-fixed.no-ol.csv",
        "format": "csv",
        "url": "https://github.com/tuetschek/e2e-cleaning/raw/master/cleaned-data/train-fixed.no-ol.csv",
        "sha256": "12a4f59ec85ddd2586244aaf166f65d1b8cd468b6227e6620108baf118d5b325",
    },
    "test": {
        "filename": "test.json",
        "format": "gem-json",
        "url": "https://raw.githubusercontent.com/jordiclive/GEM_datasets/main/e2e/test.json",
        "sha256": "e52a3cfc76fced9546c8362eb7de4c65dc64c2b935b496916c7ddfa1170b9aaa",
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_source_file(split: str, raw_dir: Path) -> Path:
    """Download one source file if needed and verify its published SHA-256."""
    try:
        source = E2E_SOURCES[split]
    except KeyError as e:
        raise ValueError(f"Unsupported E2E source split: {split!r}") from e

    raw_dir.mkdir(parents=True, exist_ok=True)
    dest = raw_dir / source["filename"]
    expected = source["sha256"]

    if dest.exists():
        actual = sha256_file(dest)
        if actual == expected:
            print(f"Using verified local source: {dest}")
            return dest
        print(f"Checksum mismatch for cached {dest}; downloading it again.")
        dest.unlink()

    tmp = dest.with_suffix(dest.suffix + ".part")
    if tmp.exists():
        tmp.unlink()
    print(f"Downloading {split} source: {source['url']}")
    request = urllib.request.Request(
        source["url"],
        headers={"User-Agent": "Elvex-paper-reproducibility/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response, tmp.open("wb") as out:
            shutil.copyfileobj(response, out)
    except Exception as e:
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"Could not download E2E {split} source: {e}") from e

    actual = sha256_file(tmp)
    if actual != expected:
        tmp.unlink(missing_ok=True)
        raise SystemExit(
            f"SHA-256 mismatch for E2E {split} source: got {actual}, expected {expected}."
        )
    tmp.replace(dest)
    return dest


def load_e2e_source(split: str, raw_dir: Path) -> list[dict[str, Any]]:
    """Load the exact public source files used by the GEM E2E configuration."""
    source = E2E_SOURCES[split]
    path = ensure_source_file(split, raw_dir)

    if source["format"] == "csv":
        with path.open("r", encoding="utf-8", newline="") as f:
            return [dict(row) for row in csv.DictReader(f)]

    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        if len(data) != 1:
            raise ValueError(f"Expected one top-level key in {path}, found {len(data)}")
        data = next(iter(data.values()))
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON list in {path}")
    rows: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict) or not item:
            continue
        rows.append({
            "meaning_representation": item["meaning_representation"],
            "target": item["references"][0] if item.get("references") else "",
            "references": list(item.get("references") or []),
        })
    return rows


def get_mr(row: dict[str, Any]) -> str:
    for key in ("input", "mr", "meaning_representation"):
        val = row.get(key)
        if isinstance(val, str) and "[" in val and "]" in val:
            return val
    raise KeyError(f"Could not find an MR field in row keys: {sorted(row)}")


def get_references(row: dict[str, Any]) -> list[str]:
    """Return every human reference supplied in GEM's references field."""
    val = row.get("references")
    if isinstance(val, (list, tuple)):
        refs = [str(x).strip() for x in val if isinstance(x, str) and x.strip()]
        if refs:
            return refs
    elif isinstance(val, str) and val.strip():
        return [val.strip()]

    # Compatibility fallback for dataset variants that expose only one target.
    for key in ("target", "ref", "reference", "output"):
        val = row.get(key)
        if isinstance(val, str) and val.strip():
            return [val.strip()]
    return []


def get_row_id(row: dict[str, Any], fallback: str) -> str:
    for key in ("gem_id", "id", "eid", "example_id"):
        val = row.get(key)
        if val is not None and str(val).strip():
            return str(val)
    return fallback


def distinct_mr_items(rows: Iterable[dict[str, Any]], split: str) -> list[dict[str, Any]]:
    """Aggregate references under each distinct MR, preserving source order."""
    by_mr: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
    for i, row in enumerate(rows, 1):
        mr = get_mr(row)
        if mr not in by_mr:
            slots = parse_e2e_mr(mr)
            by_mr[mr] = {
                "id": get_row_id(row, f"{split}-{i}"),
                "fragment_id": f"e2e_{split}_{len(by_mr) + 1:05d}",
                "split": split,
                "mr": mr,
                "expected_slots": slots,
                "n_slots": len(slots),
                "references": [],
            }
        by_mr[mr]["references"].extend(get_references(row))
    return list(by_mr.values())


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return n


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("$ " + " ".join(map(str, cmd)))
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def require_script(scripts_dir: Path, name: str) -> Path:
    p = scripts_dir / name
    if not p.exists():
        raise FileNotFoundError(f"Missing required helper script: {p}")
    return p


def summarize_items(items: list[dict[str, Any]]) -> dict[str, Any]:
    slot_counts: dict[str, int] = {s: 0 for s in sorted(SUPPORTED_SLOTS)}
    total_slots = 0
    for item in items:
        slots = item["expected_slots"]
        total_slots += len(slots)
        for slot in slots:
            slot_counts[slot] += 1
    return {
        "inputs": len(items),
        "total_slots": total_slots,
        "slot_counts": slot_counts,
        "avg_slots_per_input": total_slots / len(items) if items else 0.0,
        "references": sum(len(x.get("references", [])) for x in items),
    }


def lexical_inventory(items: Iterable[dict[str, Any]]) -> dict[str, set[str]]:
    inventory = {slot: set() for slot in sorted(SUPPORTED_SLOTS)}
    for item in items:
        for slot, value in item["expected_slots"].items():
            inventory[slot].add(clean_value(value))
    return inventory


def lexicon_coverage_report(
    train_items: list[dict[str, Any]], test_items: list[dict[str, Any]]
) -> dict[str, Any]:
    train_inventory = lexical_inventory(train_items)
    missing: dict[str, list[str]] = {slot: [] for slot in sorted(SUPPORTED_SLOTS)}
    affected: list[str] = []

    for item in test_items:
        unseen = []
        for slot, value in item["expected_slots"].items():
            cleaned = clean_value(value)
            if cleaned not in train_inventory[slot]:
                unseen.append(f"{slot}={cleaned}")
                if cleaned not in missing[slot]:
                    missing[slot].append(cleaned)
        if unseen:
            affected.append(item["fragment_id"])

    missing = {slot: sorted(values) for slot, values in missing.items() if values}
    return {
        "lexicon_source_split": "train",
        "evaluation_split": "test",
        "train_inputs": len(train_items),
        "test_inputs": len(test_items),
        "train_inventory_sizes": {
            slot: len(values) for slot, values in sorted(train_inventory.items())
        },
        "missing_test_values": missing,
        "test_inputs_with_unseen_values": len(affected),
        "all_test_values_seen_in_train": not missing,
    }


def assert_test_invariants(
    summary: dict[str, Any], expect_inputs: int, expect_slots: int, expect_references: int
) -> None:
    expected = {
        "inputs": expect_inputs,
        "total_slots": expect_slots,
        "references": expect_references,
    }
    mismatches = {
        key: (summary.get(key), value)
        for key, value in expected.items()
        if summary.get(key) != value
    }
    if mismatches:
        details = ", ".join(
            f"{key}: got {got}, expected {wanted}"
            for key, (got, wanted) in mismatches.items()
        )
        raise SystemExit(f"E2E/GEM test-set invariant failure: {details}")


def make_table(metrics_first: dict[str, Any], metrics_best: dict[str, Any]) -> str:
    def pct(x: float) -> str:
        return f"{100.0 * x:.1f}"

    return "\n".join([
        r"\begin{tabular}{@{}lrrrrrr@{}}",
        r"\toprule",
        r"Mode & Inp. & Cov. & Slots & Acc. & SER & Out. \\",
        r"\midrule",
        f"First output & {metrics_first['total_inputs']} & {pct(metrics_first['coverage'])} & {metrics_first['total_slots']} & {pct(metrics_first['slot_accuracy'])} & {pct(metrics_first['slot_omission_rate'])} & {metrics_first['avg_outputs_per_input']:.1f} \\",
        f"Best in forest & {metrics_best['total_inputs']} & {pct(metrics_best['coverage'])} & {metrics_best['total_slots']} & {pct(metrics_best['slot_accuracy'])} & {pct(metrics_best['slot_omission_rate'])} & {metrics_best['avg_outputs_per_input']:.1f} \\",
        r"\bottomrule",
        r"\end{tabular}",
        "",
    ])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--test-split", default="test")
    ap.add_argument("--lexicon-split", default="train")
    ap.add_argument("--scripts-dir", default="scripts")
    ap.add_argument("--work-dir", default="runs/full")
    ap.add_argument("--grammar-prefix", default=None)
    ap.add_argument("--elvex-bin", default="elvex")
    ap.add_argument("--run-generation", action="store_true")
    ap.add_argument("--max-items", type=int, default=None,
                    help="Limit evaluated test MRs after full test-set validation (smoke tests).")
    ap.add_argument("--max-length", default="80")
    ap.add_argument("--max-time", default=None)
    ap.add_argument("--max-items-elvex", default=None)
    ap.add_argument("--expect-inputs", type=int, default=1847)
    ap.add_argument("--expect-slots", type=int, default=11428)
    ap.add_argument("--expect-references", type=int, default=4693)
    args = ap.parse_args()

    scripts_dir = Path(args.scripts_dir).resolve()
    work_dir = Path(args.work_dir).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    if args.grammar_prefix is None:
        args.grammar_prefix = str(work_dir / "grammar" / "e2e")

    raw_dir = work_dir / "raw"
    print(
        "Loading the public E2E/GEM source files directly: "
        f"lexicon={args.lexicon_split!r}, evaluation={args.test_split!r}"
    )
    train_rows = load_e2e_source(args.lexicon_split, raw_dir)
    test_rows = load_e2e_source(args.test_split, raw_dir)
    write_jsonl(work_dir / "train_raw_rows.jsonl", train_rows)
    write_jsonl(work_dir / "test_raw_rows.jsonl", test_rows)

    train_items = distinct_mr_items(train_rows, args.lexicon_split)
    full_test_items = distinct_mr_items(test_rows, args.test_split)
    write_jsonl(work_dir / "train_items.jsonl", train_items)
    write_jsonl(work_dir / "test_items_full.jsonl", full_test_items)

    summary = summarize_items(full_test_items)
    assert_test_invariants(
        summary, args.expect_inputs, args.expect_slots, args.expect_references
    )
    (work_dir / "dataset_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print("E2E/GEM test-set invariants: OK")

    coverage = lexicon_coverage_report(train_items, full_test_items)
    (work_dir / "lexicon_coverage.json").write_text(
        json.dumps(coverage, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(coverage, indent=2, ensure_ascii=False))

    test_items = full_test_items[: args.max_items] if args.max_items is not None else full_test_items
    test_items_path = work_dir / "test_items.jsonl"
    write_jsonl(test_items_path, test_items)

    make_inputs = require_script(scripts_dir, "make_full_e2e_inputs.py")
    build_grammar = require_script(scripts_dir, "build_full_e2e_grammar.py")
    run_bench = require_script(scripts_dir, "run_elvex_benchmark.py")
    eval_slots = require_script(scripts_dir, "evaluate_slots.py")

    input_dir = work_dir / "inputs_test"
    manifest_path = work_dir / "manifest_test.jsonl"
    run([
        sys.executable, str(make_inputs),
        "--items", str(test_items_path),
        "--input-dir", str(input_dir),
        "--manifest", str(manifest_path),
    ])

    prefix = Path(args.grammar_prefix)
    rules_out = prefix.with_suffix(".rules")
    lexicon_out = prefix.with_suffix(".lexicon")
    rules_out.parent.mkdir(parents=True, exist_ok=True)
    run([
        sys.executable, str(build_grammar),
        "--lexicon-items", str(work_dir / "train_items.jsonl"),
        "--rules-out", str(rules_out),
        "--lexicon-out", str(lexicon_out),
    ])

    if not args.run_generation:
        print("Prepared validated test inputs and train-derived grammar/lexicon. Add --run-generation to run Elvex.")
        return

    if shutil.which(args.elvex_bin) is None:
        raise SystemExit(
            f"Cannot find Elvex binary {args.elvex_bin!r} on PATH. "
            "Pass --elvex-bin or set ELVEX_BIN."
        )

    outputs_path = work_dir / "outputs_test_all.jsonl"
    bench_cmd = [
        sys.executable, str(run_bench),
        "--manifest", str(manifest_path),
        "--out", str(outputs_path),
        "--prefix", str(prefix.with_suffix("")),
        "--elvex-bin", args.elvex_bin,
        "--strategy", "exhaustive",
        "--max-length", str(args.max_length),
        "--all-outputs",
    ]
    if args.max_time is not None:
        bench_cmd += ["--max-time", str(args.max_time)]
    if args.max_items_elvex is not None:
        bench_cmd += ["--max-items", str(args.max_items_elvex)]
    run(bench_cmd)

    metric_specs = [
        ("first_output", []),
        ("best_in_forest", ["--best-output"]),
        ("all_outputs", ["--all-outputs"]),
    ]
    for label, flags in metric_specs:
        run([
            sys.executable, str(eval_slots),
            "--outputs", str(outputs_path),
            "--metrics", str(work_dir / f"metrics_{label}.json"),
            "--details", str(work_dir / f"details_{label}.jsonl"),
            *flags,
        ])

    first = json.loads((work_dir / "metrics_first_output.json").read_text(encoding="utf-8"))
    best = json.loads((work_dir / "metrics_best_in_forest.json").read_text(encoding="utf-8"))
    table = make_table(first, best)
    (work_dir / "table_e2e_gem_results.tex").write_text(table, encoding="utf-8")
    print(table)


if __name__ == "__main__":
    main()
