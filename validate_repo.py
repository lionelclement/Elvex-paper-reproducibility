#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent
EXPECTED_WEBNLG_TEST = {1: 388, 2: 298, 3: 331}
PINNED_WEBNLG_COMMIT = "587fa698bec705efbefe72a235a6019c2b9b8b6c"

failures: list[str] = []
warnings: list[str] = []


def ok(message: str) -> None:
    print(f"OK   {message}")


def fail(message: str) -> None:
    print(f"FAIL {message}")
    failures.append(message)


def warn(message: str) -> None:
    print(f"WARN {message}")
    warnings.append(message)


def run(label: str, cmd: list[str], cwd: Path = ROOT) -> bool:
    print(f"\n=== {label} ===")
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(cmd, cwd=cwd, env=env)
    if proc.returncode == 0:
        ok(label)
        return True
    fail(f"{label} (exit {proc.returncode})")
    return False


def git_output(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), *args], text=True, stderr=subprocess.STDOUT
    ).strip()


def tracked_files() -> list[Path]:
    raw = subprocess.check_output(
        ["git", "-C", str(ROOT), "ls-files", "-z"]
    ).decode("utf-8")
    return [Path(p) for p in raw.split("\0") if p]


def working_files() -> list[Path]:
    """Return existing tracked and non-ignored untracked files.

    This deliberately filters paths that are still present in the Git index but
    have been deleted in the working tree, which is common while applying the
    cleanup patches before the changes are staged.
    """
    raw = subprocess.check_output(
        [
            "git", "-C", str(ROOT), "ls-files",
            "--cached", "--others", "--exclude-standard", "-z",
        ]
    ).decode("utf-8")
    result: list[Path] = []
    seen: set[Path] = set()
    for name in raw.split("\0"):
        if not name:
            continue
        rel = Path(name)
        if rel in seen or not (ROOT / rel).is_file():
            continue
        seen.add(rel)
        result.append(rel)
    return result


def check_repository_hygiene(files: Iterable[Path]) -> None:
    print("\n=== Repository hygiene ===")
    bad = []
    generated_prefixes = (
        Path("benchmark/e2e/runs"),
        Path("benchmark/webnlg/data"),
        Path("benchmark/webnlg/build"),
    )
    stale_prefixes = (
        Path("benchmark/benchmark-E2E"),
        Path("benchmark/e2e_gem_repro"),
    )

    for p in files:
        parts = p.parts
        if p.name == ".DS_Store" or "__pycache__" in parts or p.suffix == ".pyc":
            bad.append(str(p))
            continue
        if ".venv" in parts or any(p == x or x in p.parents for x in generated_prefixes):
            bad.append(str(p))
            continue
        if p.suffix == ".log" or p.name in {"log.diff", "log.html"}:
            bad.append(str(p))
            continue
        if any(p == x or x in p.parents for x in stale_prefixes):
            bad.append(str(p))

    if bad:
        fail("tracked generated/stale files: " + ", ".join(bad[:10]))
        if len(bad) > 10:
            print(f"     ... and {len(bad) - 10} more")
    else:
        ok("no generated artifacts, caches, or obsolete benchmark trees are tracked")

    try:
        pinned = (ROOT / "ELVEX_COMMIT").read_text(encoding="utf-8").strip()
    except OSError as exc:
        fail(f"cannot read ELVEX_COMMIT: {exc}")
        return
    if re.fullmatch(r"[0-9a-f]{40}", pinned):
        ok(f"ELVEX_COMMIT is a full Git commit: {pinned}")
    else:
        fail(f"ELVEX_COMMIT is not a 40-character hexadecimal commit: {pinned!r}")


def check_python_syntax(files: Iterable[Path]) -> None:
    print("\n=== Python syntax ===")
    count = 0
    for rel in files:
        if rel.suffix != ".py":
            continue
        path = ROOT / rel
        try:
            compile(path.read_text(encoding="utf-8"), str(rel), "exec")
        except Exception as exc:
            fail(f"Python syntax: {rel}: {exc}")
        count += 1
    if not any("Python syntax:" in x for x in failures):
        ok(f"{count} working-tree Python files parse successfully")


def check_shell_syntax(files: Iterable[Path]) -> None:
    print("\n=== Shell syntax ===")
    shell_files = [p for p in files if p.suffix == ".sh" or p == Path("benchmark/webnlg/run")]
    bad = 0
    for rel in shell_files:
        proc = subprocess.run(["bash", "-n", str(ROOT / rel)])
        if proc.returncode != 0:
            fail(f"shell syntax: {rel}")
            bad += 1
    if bad == 0:
        ok(f"{len(shell_files)} working-tree shell entry points pass bash -n")


def read_elvex_metrics(path: Path) -> dict[str, str]:
    header = values = None
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = raw.split("\t")
        if parts and parts[0] == "ELVEX_METRICS_HEADER":
            header = parts[1:]
        elif parts and parts[0] == "ELVEX_METRICS":
            values = parts[1:]
    if not header or not values or len(header) != len(values):
        return {}
    return dict(zip(header, values))


def count_nonempty_lines(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip())


def valid_support_output(line: str) -> bool:
    s = " ".join(line.lower().split())
    return "pays notice" not in s and "takes attention" not in s


def check_support_artifacts() -> None:
    print("\n=== Controlled support-context artifacts ===")
    base = ROOT / "test/paper_support_context"
    results = base / "results.tsv"
    if not results.exists():
        fail("missing test/paper_support_context/results.tsv")
        return

    with results.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))

    expected_keys = {(mode, n) for mode in ("full", "no_context") for n in range(1, 8)}
    got_keys = {(r["mode"], int(r["N"])) for r in rows}
    if got_keys != expected_keys:
        fail(f"support-context results rows differ from N=1..7 FULL/NO-CONTEXT: {sorted(got_keys)}")
        return

    row_map = {(r["mode"], int(r["N"])): r for r in rows}
    for mode, n in sorted(expected_keys):
        row = row_map[(mode, n)]
        expected_generated = 2**n if mode == "full" else 4**n
        expected_valid = 2**n
        out_path = base / f"{mode}_N{n}.out"
        status_path = base / f"{mode}_N{n}.status"
        metrics_path = base / f"{mode}_N{n}.metrics"
        for p in (out_path, status_path, metrics_path):
            if not p.exists():
                fail(f"missing controlled-ablation artifact: {p.relative_to(ROOT)}")
                continue
        if not all(p.exists() for p in (out_path, status_path, metrics_path)):
            continue

        lines = [x.strip() for x in out_path.read_text(encoding="utf-8", errors="replace").splitlines() if x.strip()]
        valid = sum(valid_support_output(x) for x in lines)
        metrics = read_elvex_metrics(metrics_path)

        checks = [
            (status_path.read_text(encoding="utf-8").strip() == "ok", "status"),
            (row["status"] == "ok", "results.tsv status"),
            (int(row["generated"]) == expected_generated, "generated formula"),
            (int(row["expected"]) == expected_generated, "stored expected formula"),
            (len(lines) == expected_generated, "output line count"),
            (int(row["valid"]) == expected_valid, "valid formula"),
            (int(row["expected_valid"]) == expected_valid, "stored expected-valid formula"),
            (valid == expected_valid, "output validity count"),
            (metrics.get("enumerated_outputs") == str(expected_generated), "metrics enumerated_outputs"),
            (metrics.get("chart_items_inserted") == row["chart_items"], "chart items"),
            (metrics.get("packed_nodes") == row["packed_nodes"], "packed nodes"),
            (metrics.get("saturation_passes") == row["sat_passes"], "saturation passes"),
            (metrics.get("max_passes_per_saturate") == row["max_sat_passes"], "max saturation passes"),
        ]
        for condition, label in checks:
            if not condition:
                fail(f"support-context {mode} N={n}: {label} mismatch")

    for n in range(1, 8):
        full = row_map[("full", n)]
        nc = row_map[("no_context", n)]
        if full["sat_passes"] != nc["sat_passes"]:
            fail(f"support-context N={n}: FULL/NO-CONTEXT saturation-pass mismatch")
        if full["max_sat_passes"] != nc["max_sat_passes"]:
            fail(f"support-context N={n}: FULL/NO-CONTEXT max-saturation mismatch")

    if not any(x.startswith("support-context") or "controlled-ablation artifact" in x for x in failures):
        ok("stored FULL/NO-CONTEXT outputs, formulas, metrics, and saturation counts are mutually consistent")


def check_webnlg_pin() -> None:
    print("\n=== WebNLG source pin ===")
    path = ROOT / "benchmark/webnlg/user/sources.json"
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"cannot read {path.relative_to(ROOT)}: {exc}")
        return
    sources = cfg.get("sources", [])
    if len(sources) != 1:
        fail(f"expected exactly one WebNLG source, found {len(sources)}")
        return
    source = sources[0]
    revision = source.get("revision")
    if revision != PINNED_WEBNLG_COMMIT:
        fail(f"WebNLG revision is {revision!r}, expected {PINNED_WEBNLG_COMMIT}")
    else:
        ok(f"WebNLG repository pinned to {revision}")

    local_repo = ROOT / str(source.get("path", ""))
    if (local_repo / ".git").exists():
        try:
            head = subprocess.check_output(
                ["git", "-C", str(local_repo), "rev-parse", "HEAD"], text=True
            ).strip()
            if head == revision:
                ok("downloaded WebNLG repository HEAD matches the pin")
            else:
                fail(f"downloaded WebNLG repository HEAD {head} != pinned {revision}")
        except subprocess.CalledProcessError as exc:
            fail(f"cannot inspect downloaded WebNLG repository: {exc}")
    else:
        warn("downloaded WebNLG repository is absent; source pin was checked statically")


def check_webnlg_summaries(require_generated: bool) -> None:
    print("\n=== WebNLG generated results ===")
    report_dir = ROOT / "benchmark/webnlg/build/reports"
    present = []
    for size in (1, 2, 3):
        summary = report_dir / f"comparison_{size}_triples.summary.json"
        report = report_dir / f"comparison_{size}_triples.tsv"
        if not summary.exists() or not report.exists():
            if require_generated:
                fail(f"missing WebNLG size-{size} report/summary")
            else:
                warn(f"WebNLG size-{size} generated report is absent")
            continue
        present.append(size)
        data = json.loads(summary.read_text(encoding="utf-8"))
        expected_inputs = EXPECTED_WEBNLG_TEST[size]
        inputs = int(data.get("inputs", -1))
        generated = int(data.get("generated_inputs", -1))
        ok_process = int(data.get("process_ok", -1))
        failed_process = int(data.get("process_failed", -1))
        expected_coverage = 100.0 * generated / inputs if inputs > 0 else -1.0
        coverage = float(data.get("coverage_percent", -1.0))
        report_rows = max(0, count_nonempty_lines(report) - 1)

        checks = [
            (data.get("triples") == size, "triple-count label"),
            (inputs == expected_inputs, f"official test input count ({expected_inputs})"),
            (ok_process == inputs, "process_ok"),
            (failed_process == 0, "process_failed"),
            (0 <= generated <= inputs, "generated input count"),
            (abs(coverage - expected_coverage) <= 0.00011, "coverage arithmetic"),
            (report_rows == inputs, "TSV row count"),
        ]
        for condition, label in checks:
            if not condition:
                fail(f"WebNLG size {size}: {label} mismatch")
        if all(condition for condition, _ in checks):
            ok(
                f"WebNLG size {size}: {inputs} inputs, {generated} generated, "
                f"{coverage:.4f}% coverage, 0 process failures"
            )

    if present and len(present) != 3:
        fail(f"partial WebNLG report set present: {present}")


def check_elvex_commands(args: argparse.Namespace) -> None:
    print("\n=== Elvex commands ===")
    elvex = shutil.which(os.environ.get("ELVEX_BIN", "elvex"))
    elvexlexicon = shutil.which(os.environ.get("ELVEXLEXICON_BIN", "elvexlexicon"))
    if elvex:
        ok(f"elvex: {elvex}")
        with tempfile.TemporaryDirectory(prefix="elvex-lexical-context-validation-") as directory:
            fresh_results = Path(directory) / "results.tsv"
            generated = run(
                "Lexical-context fresh Elvex run",
                [
                    sys.executable,
                    "benchmark/lexical-context/run_benchmark.py",
                    "--elvex",
                    elvex,
                    "--output",
                    str(fresh_results),
                ],
            )
            if generated:
                run(
                    "Lexical-context fresh-result consistency",
                    [
                        sys.executable,
                        "benchmark/lexical-context/check_results.py",
                        "--results",
                        str(fresh_results),
                    ],
                )
        if args.run_extended_context:
            with tempfile.TemporaryDirectory(prefix="elvex-context-extended-") as directory:
                extended = Path(directory)
                repeated_raw = extended / "repeated-results.tsv"
                timing_summary = extended / "timing-summary.tsv"
                timing_environment = extended / "timing-environment.tsv"
                heterogeneous = extended / "heterogeneous-results.tsv"
                run(
                    "Lexical-context repeated timings",
                    [
                        sys.executable,
                        "benchmark/lexical-context/run_repeated.py",
                        "--elvex",
                        elvex,
                        "--repeats",
                        str(args.context_repeats),
                        "--raw-output",
                        str(repeated_raw),
                        "--summary-output",
                        str(timing_summary),
                        "--environment-output",
                        str(timing_environment),
                    ],
                )
                generated = run(
                    "Lexical-context heterogeneous composition",
                    [
                        sys.executable,
                        "benchmark/lexical-context/run_heterogeneous.py",
                        "--elvex",
                        elvex,
                        "--max-n",
                        "4",
                        "--output",
                        str(heterogeneous),
                    ],
                )
                if generated:
                    run(
                        "Lexical-context heterogeneous consistency",
                        [
                            sys.executable,
                            "benchmark/lexical-context/check_heterogeneous_results.py",
                            "--results",
                            str(heterogeneous),
                            "--require-complete",
                        ],
                    )
    elif args.require_elvex or args.run_extended_context:
        fail(
            "elvex not found on PATH; install Elvex or set ELVEX_BIN to its executable"
        )
    else:
        warn("elvex not found; fresh lexical-context experiment skipped")

    if elvex and elvexlexicon:
        ok(f"elvexlexicon: {elvexlexicon}")
        run(
            "Elvex regression suite",
            ["bash", "test/run-regression.sh", elvex, elvexlexicon],
        )
    elif args.require_elvex:
        fail(
            "elvexlexicon not found on PATH; install Elvex or set "
            "ELVEXLEXICON_BIN to its executable"
        )
    else:
        warn("elvexlexicon not found; executable regression suite skipped")


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate the Elvex paper reproducibility repository")
    ap.add_argument(
        "--require-generated",
        action="store_true",
        help="Fail if local generated E2E/WebNLG benchmark artifacts are absent.",
    )
    ap.add_argument(
        "--require-elvex",
        action="store_true",
        help="Fail if elvex/elvexlexicon are unavailable; otherwise executable regression tests are optional.",
    )
    ap.add_argument(
        "--run-extended-context",
        action="store_true",
        help="Run repeated lexical timings and all heterogeneous context panels.",
    )
    ap.add_argument(
        "--context-repeats",
        type=int,
        default=30,
        help="Measured repetitions for --run-extended-context (default: 30).",
    )
    args = ap.parse_args()
    if args.context_repeats < 2:
        ap.error("--context-repeats must be at least 2")

    try:
        tracked = tracked_files()
        files = working_files()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"FAILED: cannot inspect Git repository: {exc}", file=sys.stderr)
        return 2

    check_repository_hygiene(tracked)
    run("git diff HEAD --check", ["git", "diff", "HEAD", "--check"])
    check_python_syntax(files)
    check_shell_syntax(files)

    run("E2E unit tests", [sys.executable, "-m", "unittest", "discover", "-s", "benchmark/e2e/tests", "-v"])

    e2e_metrics = ROOT / "benchmark/e2e/runs/full/metrics_all_outputs.json"
    if e2e_metrics.exists():
        run("E2E generated-result consistency", [sys.executable, "benchmark/e2e/check_results.py"])
    elif args.require_generated:
        fail("E2E full generated results are absent (benchmark/e2e/runs/full)")
    else:
        warn("E2E full generated results are absent; generated-result consistency check skipped")

    run(
        "Lexical-context unit tests",
        [sys.executable, "-m", "unittest", "discover", "-s", "benchmark/lexical-context/tests", "-v"],
    )
    run(
        "Lexical-context result consistency",
        [sys.executable, "benchmark/lexical-context/check_results.py"],
    )
    run(
        "Lexical-context timing snapshot consistency",
        [sys.executable, "benchmark/lexical-context/check_timing_results.py"],
    )

    run("WebNLG unit tests", [sys.executable, "-m", "unittest", "discover", "-s", "benchmark/webnlg/tests", "-v"])
    check_webnlg_pin()

    webnlg_triples = ROOT / "benchmark/webnlg/data/processed/triples.jsonl"
    if webnlg_triples.exists():
        run("WebNLG extraction/data invariants", [sys.executable, "benchmark/webnlg/scripts/check_webnlg_data.py"])
    elif args.require_generated:
        fail("WebNLG extracted data are absent (benchmark/webnlg/data/processed/triples.jsonl)")
    else:
        warn("WebNLG extracted data are absent; data invariant check skipped")

    check_webnlg_summaries(args.require_generated)

    webnlg_main_input = ROOT / "benchmark/webnlg/user/main.input"
    if webnlg_main_input.exists():
        run("WebNLG generated project structure", [sys.executable, "benchmark/webnlg/scripts/validate_project.py"])
    else:
        warn(
            "WebNLG user/main.input is absent; generated project-structure check skipped "
            "(this file is an ignored single-input scratch artifact, not a benchmark result)"
        )

    check_support_artifacts()
    check_elvex_commands(args)

    print("\n=== Final result ===")
    if failures:
        print(f"FAILED: {len(failures)} issue(s)")
        for item in failures:
            print(f"  - {item}")
        if warnings:
            print(f"Warnings: {len(warnings)}")
        return 1

    if warnings:
        print(f"OK with {len(warnings)} warning(s)")
        for item in warnings:
            print(f"  - {item}")
    else:
        print("OK: repository, tests, and available experiment artifacts are consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
