#!/usr/bin/env python3
"""Validate the committed lexical-context ablation snapshot.

This checker deliberately validates structural results, not machine-dependent
timings.  It is suitable for CI and for the top-level repository validator on
machines where the pinned Elvex executable is unavailable.
"""
from __future__ import annotations

import argparse
import csv
import math
from collections import Counter, defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
CONDITIONS = ("FULL", "NO-CONTEXT", "PRE-SPECIFIED")


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def as_int(row: dict[str, str], field: str) -> int:
    try:
        return int(row[field])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            f"{row.get('condition', '?')} {row.get('case_id', '?')}: "
            f"invalid integer {field}={row.get(field)!r}"
        ) from exc


def as_float(row: dict[str, str], field: str) -> float:
    try:
        return float(row[field])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            f"{row.get('condition', '?')} {row.get('case_id', '?')}: "
            f"invalid number {field}={row.get(field)!r}"
        ) from exc


def expected_surface(case: dict[str, str]) -> str:
    return f"John {case['verb']} {case['article']} {case['noun']} ."


def validate_rows(
    cases: list[dict[str, str]], results: list[dict[str, str]]
) -> dict[str, dict[str, float | int]]:
    require(cases, "cases.tsv is empty")
    require(results, "results.tsv is empty")

    case_ids = [row.get("case_id", "") for row in cases]
    require(all(case_ids), "cases.tsv contains an empty case_id")
    require(len(case_ids) == len(set(case_ids)), "cases.tsv contains duplicate case_id values")

    supports = {row["support"] for row in cases}
    require(len(cases) == 12, f"expected the reported 12-case snapshot, found {len(cases)}")
    require(len(supports) == 9, f"expected the reported 9 support verbs, found {len(supports)}")

    expected_keys = {(condition, case_id) for condition in CONDITIONS for case_id in case_ids}
    keys = [(row.get("condition", ""), row.get("case_id", "")) for row in results]
    counts = Counter(keys)
    require(
        set(keys) == expected_keys,
        "results.tsv does not contain exactly every condition/case pair",
    )
    require(
        all(count == 1 for count in counts.values()),
        "results.tsv contains duplicate condition/case rows",
    )

    cases_by_id = {row["case_id"]: row for row in cases}
    rows_by_case: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    summary: dict[str, dict[str, float | int]] = {}

    for row in results:
        condition = row["condition"]
        case_id = row["case_id"]
        case = cases_by_id[case_id]
        rows_by_case[case_id][condition] = row

        require(row.get("predicate") == case["predicate"], f"{condition} {case_id}: predicate mismatch")
        require(row.get("expected") == expected_surface(case), f"{condition} {case_id}: expected surface mismatch")

        generated = as_int(row, "unique_outputs")
        valid = as_int(row, "valid_outputs")
        spurious = as_int(row, "spurious_outputs")
        fraction = as_float(row, "valid_fraction")
        require(generated == valid + spurious, f"{condition} {case_id}: output partition mismatch")
        require(math.isclose(fraction, valid / generated, abs_tol=1e-8), f"{condition} {case_id}: valid_fraction mismatch")

        if condition in {"FULL", "PRE-SPECIFIED"}:
            require((generated, valid, spurious) == (1, 1, 0), f"{condition} {case_id}: expected one valid output only")
        else:
            require(
                (generated, valid, spurious) == (len(supports), 1, len(supports) - 1),
                f"NO-CONTEXT {case_id}: expected one valid output plus every incompatible support",
            )

    for case_id, by_condition in rows_by_case.items():
        full = by_condition["FULL"]
        prespecified = by_condition["PRE-SPECIFIED"]
        no_context = by_condition["NO-CONTEXT"]
        require(
            full["expected"] == prespecified["expected"] == no_context["expected"],
            f"{case_id}: conditions disagree on the compatible realization",
        )
        require(
            as_int(no_context, "valid_outputs") == as_int(full, "valid_outputs"),
            f"{case_id}: the ablation lost the compatible realization instead of overgenerating",
        )

    for condition in CONDITIONS:
        selected = [row for row in results if row["condition"] == condition]
        generated = sum(as_int(row, "unique_outputs") for row in selected)
        valid = sum(as_int(row, "valid_outputs") for row in selected)
        spurious = sum(as_int(row, "spurious_outputs") for row in selected)
        summary[condition] = {
            "cases": len(selected),
            "generated": generated,
            "valid": valid,
            "spurious": spurious,
            "valid_percent": 100.0 * valid / generated,
        }

    require(summary["FULL"]["generated"] == 12, "FULL total differs from the reported result")
    require(summary["PRE-SPECIFIED"]["generated"] == 12, "PRE-SPECIFIED total differs from the reported result")
    require(summary["NO-CONTEXT"]["generated"] == 108, "NO-CONTEXT total differs from the reported result")
    require(summary["NO-CONTEXT"]["spurious"] == 96, "NO-CONTEXT spurious total differs from the reported result")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=HERE / "cases.tsv")
    parser.add_argument("--results", type=Path, default=HERE / "reference-results.tsv")
    args = parser.parse_args()

    try:
        summary = validate_rows(read_tsv(args.cases), read_tsv(args.results))
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print("condition\tcases\tgenerated\tvalid\tspurious\tvalid_%")
    for condition in CONDITIONS:
        row = summary[condition]
        print(
            f"{condition}\t{row['cases']}\t{row['generated']}\t{row['valid']}\t"
            f"{row['spurious']}\t{row['valid_percent']:.3f}"
        )
    print("OK: lexical-context snapshot is internally consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
