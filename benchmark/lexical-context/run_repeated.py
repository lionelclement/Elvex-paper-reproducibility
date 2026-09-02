#!/usr/bin/env python3
"""Repeat the lexical-context ablation and summarize timing variability."""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import os
import platform
import statistics
import subprocess
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import check_results
import run_benchmark


HERE = Path(__file__).resolve().parent
CONDITIONS = ("FULL", "NO-CONTEXT", "PRE-SPECIFIED")
CONDITION_ORDERS = tuple(itertools.permutations(CONDITIONS))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cpu_description() -> str:
    description = platform.processor().strip()
    if description:
        return description
    try:
        process = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            text=True,
            capture_output=True,
        )
        if process.returncode == 0 and process.stdout.strip():
            return process.stdout.strip()
    except OSError:
        pass
    return platform.machine()


def physical_memory_bytes() -> str:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return str(int(pages) * int(page_size))
    except (AttributeError, OSError, TypeError, ValueError):
        return "unknown"


def percentile(values: list[float], probability: float) -> float:
    """Linear-interpolated sample percentile (Hyndman-Fan type 7)."""
    if not values:
        raise ValueError("cannot compute a percentile of an empty sample")
    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must be between zero and one")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + fraction * (ordered[upper] - ordered[lower])


def summarize(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        grouped[row["condition"]].append(float(row["wall_ms"]))

    summary = []
    for condition in CONDITIONS:
        values = grouped[condition]
        if not values:
            raise ValueError(f"missing repeated timing rows for {condition}")
        q1 = percentile(values, 0.25)
        q3 = percentile(values, 0.75)
        summary.append({
            "condition": condition,
            "runs": str(len(values)),
            "median_ms": f"{statistics.median(values):.3f}",
            "q1_ms": f"{q1:.3f}",
            "q3_ms": f"{q3:.3f}",
            "iqr_ms": f"{q3 - q1:.3f}",
            "p90_ms": f"{percentile(values, 0.90):.3f}",
            "p95_ms": f"{percentile(values, 0.95):.3f}",
            "max_ms": f"{max(values):.3f}",
        })
    return summary


def write_tsv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=fields, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def run_iteration(
    elvex: str,
    order: tuple[str, ...],
    output: Path,
) -> list[dict[str, str]]:
    command = [
        sys.executable,
        str(HERE / "run_benchmark.py"),
        "--elvex",
        elvex,
        "--conditions",
        ",".join(order),
        "--output",
        str(output),
    ]
    process = subprocess.run(command, text=True, capture_output=True)
    if process.returncode != 0:
        raise RuntimeError(
            f"lexical-context iteration failed ({process.returncode})\n"
            f"stdout:\n{process.stdout}\nstderr:\n{process.stderr}"
        )
    rows = check_results.read_tsv(output)
    cases = check_results.read_tsv(HERE / "cases.tsv")
    check_results.validate_rows(cases, rows)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--elvex", help="path to the elvex executable")
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--repeats", type=int, default=30)
    parser.add_argument(
        "--raw-output", type=Path, default=HERE / "repeated-results.tsv"
    )
    parser.add_argument(
        "--summary-output", type=Path, default=HERE / "timing-summary.tsv"
    )
    parser.add_argument(
        "--environment-output", type=Path, default=HERE / "timing-environment.tsv"
    )
    args = parser.parse_args()

    if args.warmups < 0:
        parser.error("--warmups must be non-negative")
    if args.repeats < 2:
        parser.error("--repeats must be at least 2")

    elvex = run_benchmark.resolve_elvex(args.elvex)
    raw_rows: list[dict[str, str]] = []

    with tempfile.TemporaryDirectory(prefix="elvex-context-repeated-") as directory:
        temporary = Path(directory)
        for warmup in range(args.warmups):
            order = CONDITION_ORDERS[warmup % len(CONDITION_ORDERS)]
            run_iteration(elvex, order, temporary / f"warmup-{warmup + 1}.tsv")

        for repeat in range(args.repeats):
            order = CONDITION_ORDERS[repeat % len(CONDITION_ORDERS)]
            rows = run_iteration(elvex, order, temporary / f"repeat-{repeat + 1}.tsv")
            for condition in CONDITIONS:
                selected = [row for row in rows if row["condition"] == condition]
                raw_rows.append({
                    "repeat": str(repeat + 1),
                    "order": ",".join(order),
                    "condition": condition,
                    "cases": str(len(selected)),
                    "generated": str(sum(int(row["unique_outputs"]) for row in selected)),
                    "valid": str(sum(int(row["valid_outputs"]) for row in selected)),
                    "spurious": str(sum(int(row["spurious_outputs"]) for row in selected)),
                    "wall_ms": f"{sum(float(row['wall_ms']) for row in selected):.3f}",
                })

    raw_fields = [
        "repeat", "order", "condition", "cases", "generated", "valid",
        "spurious", "wall_ms",
    ]
    summary_fields = [
        "condition", "runs", "median_ms", "q1_ms", "q3_ms", "iqr_ms",
        "p90_ms", "p95_ms", "max_ms",
    ]
    summary_rows = summarize(raw_rows)
    write_tsv(args.raw_output, raw_rows, raw_fields)
    write_tsv(args.summary_output, summary_rows, summary_fields)

    pin = (HERE.parents[1] / "ELVEX_COMMIT").read_text(encoding="utf-8").strip()
    environment_rows = [
        {"key": "timestamp_utc", "value": datetime.now(timezone.utc).isoformat()},
        {"key": "platform", "value": platform.platform()},
        {"key": "machine", "value": platform.machine()},
        {"key": "processor", "value": cpu_description()},
        {"key": "physical_memory_bytes", "value": physical_memory_bytes()},
        {"key": "python", "value": platform.python_version()},
        {"key": "elvex_executable", "value": elvex},
        {"key": "elvex_sha256", "value": sha256_file(Path(elvex))},
        {"key": "elvex_commit_metadata", "value": pin},
        {"key": "warmups", "value": str(args.warmups)},
        {"key": "repeats", "value": str(args.repeats)},
        {"key": "condition_order", "value": "balanced six-permutation cycle"},
    ]
    write_tsv(args.environment_output, environment_rows, ["key", "value"])

    print("condition\truns\tmedian_ms\tq1_ms\tq3_ms\tiqr_ms\tp90_ms\tp95_ms\tmax_ms")
    for row in summary_rows:
        print("\t".join(row[field] for field in summary_fields))
    print(f"wrote {args.raw_output}")
    print(f"wrote {args.summary_output}")
    print(f"wrote {args.environment_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
