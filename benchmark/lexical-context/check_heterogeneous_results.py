#!/usr/bin/env python3
"""Validate structural results from run_heterogeneous.py."""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

import run_heterogeneous


HERE = Path(__file__).resolve().parent
CONDITIONS = ("FULL", "NO-CONTEXT")


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def validate(rows: list[dict[str, str]], panels: list[dict[str, str]], complete: bool) -> None:
    run_heterogeneous.require(rows, "heterogeneous result file is empty")
    panel_by_id = {panel["panel_id"]: panel for panel in panels}
    keys = [(row.get("condition", ""), row.get("panel_id", "")) for row in rows]
    counts = Counter(keys)
    run_heterogeneous.require(
        all(count == 1 for count in counts.values()),
        "heterogeneous results contain duplicate condition/panel rows",
    )
    for row in rows:
        condition = row.get("condition", "")
        panel_id = row.get("panel_id", "")
        run_heterogeneous.require(condition in CONDITIONS, f"unknown condition {condition!r}")
        run_heterogeneous.require(panel_id in panel_by_id, f"unknown panel {panel_id!r}")
        panel = panel_by_id[panel_id]
        run_heterogeneous.require(row.get("n") == panel["n"], f"{panel_id}: n mismatch")
        run_heterogeneous.require(
            row.get("case_ids") == panel["case_ids"], f"{panel_id}: case list mismatch"
        )
        run_heterogeneous.validate_result_row(row)

    if complete:
        expected = {
            (condition, panel["panel_id"])
            for condition in CONDITIONS
            for panel in panels
        }
        run_heterogeneous.require(set(keys) == expected, "full result file is incomplete")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--results", type=Path, default=HERE / "heterogeneous-results.tsv"
    )
    parser.add_argument(
        "--panels", type=Path, default=HERE / "heterogeneous-panels.tsv"
    )
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()

    try:
        rows = read_tsv(args.results)
        panels = read_tsv(args.panels)
        validate(rows, panels, args.require_complete)
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(f"OK: {len(rows)} heterogeneous condition/panel rows are consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
