#!/usr/bin/env python3
"""Validate the committed lexical-context timing snapshot used in the paper."""
from __future__ import annotations

import argparse
import csv
import itertools
from pathlib import Path

import run_repeated


HERE = Path(__file__).resolve().parent
CONDITIONS = run_repeated.CONDITIONS
CONDITION_ORDERS = tuple(itertools.permutations(CONDITIONS))
EXPECTED_PAPER_VALUES = {
    "FULL": {"median_ms": "18.480", "p95_ms": "19.920"},
    "NO-CONTEXT": {"median_ms": "26.298", "p95_ms": "27.824"},
    "PRE-SPECIFIED": {"median_ms": "18.931", "p95_ms": "19.979"},
}


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_raw(rows: list[dict[str, str]], repeats: int) -> None:
    require(len(rows) == repeats * len(CONDITIONS), (
        f"expected {repeats * len(CONDITIONS)} timing rows, found {len(rows)}"
    ))

    by_repeat: dict[int, dict[str, dict[str, str]]] = {}
    for row in rows:
        try:
            repeat = int(row["repeat"])
        except (KeyError, ValueError) as exc:
            raise ValueError(f"invalid repeat value: {row.get('repeat')!r}") from exc
        condition = row.get("condition", "")
        require(condition in CONDITIONS, f"unknown condition {condition!r}")
        require(condition not in by_repeat.setdefault(repeat, {}), (
            f"duplicate {condition} row for repeat {repeat}"
        ))
        by_repeat[repeat][condition] = row

    require(set(by_repeat) == set(range(1, repeats + 1)), (
        f"repeat ids must be exactly 1..{repeats}"
    ))

    for repeat in range(1, repeats + 1):
        rows_for_repeat = by_repeat[repeat]
        require(set(rows_for_repeat) == set(CONDITIONS), (
            f"repeat {repeat} does not contain all three conditions"
        ))
        expected_order = CONDITION_ORDERS[(repeat - 1) % len(CONDITION_ORDERS)]
        expected_order_text = ",".join(expected_order)
        require(
            {row["order"] for row in rows_for_repeat.values()} == {expected_order_text},
            f"repeat {repeat}: unexpected condition order",
        )
        for condition, row in rows_for_repeat.items():
            require(row.get("cases") == "12", f"repeat {repeat} {condition}: cases != 12")
            expected = {
                "FULL": ("12", "12", "0"),
                "PRE-SPECIFIED": ("12", "12", "0"),
                "NO-CONTEXT": ("108", "12", "96"),
            }[condition]
            actual = (row.get("generated"), row.get("valid"), row.get("spurious"))
            require(actual == expected, (
                f"repeat {repeat} {condition}: structural counts {actual} != {expected}"
            ))
            try:
                require(float(row["wall_ms"]) >= 0.0, (
                    f"repeat {repeat} {condition}: negative wall_ms"
                ))
            except (KeyError, ValueError) as exc:
                raise ValueError(
                    f"repeat {repeat} {condition}: invalid wall_ms={row.get('wall_ms')!r}"
                ) from exc


def validate_summary(
    raw_rows: list[dict[str, str]], summary_rows: list[dict[str, str]]
) -> None:
    calculated = run_repeated.summarize(raw_rows)
    require(summary_rows == calculated, (
        "reference-timing-summary.tsv does not exactly match statistics "
        "recomputed from reference-repeated-results.tsv"
    ))

    by_condition = {row["condition"]: row for row in summary_rows}
    require(set(by_condition) == set(CONDITIONS), "timing summary has wrong conditions")
    for condition, expected in EXPECTED_PAPER_VALUES.items():
        row = by_condition[condition]
        require(row.get("runs") == "30", f"{condition}: expected 30 measured runs")
        for field, value in expected.items():
            require(row.get(field) == value, (
                f"{condition}: published {field} should be {value}, found {row.get(field)!r}"
            ))


def validate_environment(rows: list[dict[str, str]], repeats: int) -> None:
    require(rows, "reference-timing-environment.tsv is empty")
    env = {row.get("key", ""): row.get("value", "") for row in rows}
    required_keys = {
        "timestamp_utc", "platform", "machine", "processor",
        "physical_memory_bytes", "python", "elvex_executable", "elvex_sha256",
        "elvex_commit_metadata", "warmups", "repeats", "condition_order",
    }
    require(required_keys <= set(env), "timing environment is missing required metadata")
    require(env["warmups"] == "2", "reference timing run must use two warm-ups")
    require(env["repeats"] == str(repeats), f"reference timing run must use {repeats} repeats")
    require(env["condition_order"] == "balanced six-permutation cycle", (
        "reference timing run must use the balanced six-permutation cycle"
    ))

    pinned = (HERE.parents[1] / "ELVEX_COMMIT").read_text(encoding="utf-8").strip()
    require(env["elvex_commit_metadata"] == pinned, (
        "timing environment Elvex commit does not match ELVEX_COMMIT"
    ))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw", type=Path, default=HERE / "reference-repeated-results.tsv"
    )
    parser.add_argument(
        "--summary", type=Path, default=HERE / "reference-timing-summary.tsv"
    )
    parser.add_argument(
        "--environment", type=Path, default=HERE / "reference-timing-environment.tsv"
    )
    parser.add_argument("--repeats", type=int, default=30)
    args = parser.parse_args()

    try:
        raw_rows = read_tsv(args.raw)
        summary_rows = read_tsv(args.summary)
        environment_rows = read_tsv(args.environment)
        validate_raw(raw_rows, args.repeats)
        validate_summary(raw_rows, summary_rows)
        validate_environment(environment_rows, args.repeats)
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print("condition\truns\tmedian_ms\tp95_ms")
    for row in summary_rows:
        print(f"{row['condition']}\t{row['runs']}\t{row['median_ms']}\t{row['p95_ms']}")
    print("OK: lexical-context timing snapshot reproduces the published median/p95 values")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
