#!/usr/bin/env python3
"""Run a heterogeneous multi-construction FULL / NO-CONTEXT stress test."""
from __future__ import annotations

import argparse
import csv
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import run_benchmark


HERE = Path(__file__).resolve().parent
CONDITIONS = {
    "FULL": HERE / "heterogeneous-full.rules",
    "NO-CONTEXT": HERE / "heterogeneous-no-context.rules",
}
METRIC_COLUMNS = {
    "internal_total_ms": "total_wall_ms",
    "chart_items": "chart_items_inserted",
    "packed_nodes": "packed_nodes",
    "forest_edges": "forest_edges",
    "saturation_passes": "saturation_passes",
    "max_saturation_passes": "max_passes_per_saturate",
    "rss_kb": "process_hwm_rss_kb",
}
CONTEXT_FIELDS = ("first", "second", "third", "fourth")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def validate_panels(
    panels: list[dict[str, str]], cases: list[dict[str, str]], *, balanced: bool
) -> None:
    require(panels, "panel file is empty")
    cases_by_id = {row["case_id"]: row for row in cases}
    require(len(cases_by_id) == len(cases), "cases.tsv has duplicate case identifiers")
    panel_ids = [row.get("panel_id", "") for row in panels]
    require(all(panel_ids), "panel file contains an empty panel_id")
    require(len(panel_ids) == len(set(panel_ids)), "panel file has duplicate panel identifiers")

    by_n: dict[int, list[dict[str, str]]] = defaultdict(list)
    for panel in panels:
        try:
            n = int(panel["n"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"{panel.get('panel_id', '?')}: invalid n") from exc
        ids = [value for value in panel.get("case_ids", "").split(",") if value]
        require(1 <= n <= 4, f"{panel['panel_id']}: n must be in 1..4")
        require(len(ids) == n, f"{panel['panel_id']}: expected {n} case identifiers")
        require(len(ids) == len(set(ids)), f"{panel['panel_id']}: repeated case identifier")
        unknown = [case_id for case_id in ids if case_id not in cases_by_id]
        require(not unknown, f"{panel['panel_id']}: unknown cases {unknown}")
        supports = [cases_by_id[case_id]["support"] for case_id in ids]
        require(
            len(supports) == len(set(supports)),
            f"{panel['panel_id']}: support verbs must be distinct within a panel",
        )
        by_n[n].append(panel)

    if balanced:
        inventory = {row["support"] for row in cases}
        require(set(by_n) == {1, 2, 3, 4}, "default panels must cover n=1..4")
        for n in range(1, 5):
            selected = by_n[n]
            require(len(selected) == 9, f"n={n}: expected nine cyclic panels")
            frequencies: Counter[str] = Counter()
            for panel in selected:
                for case_id in panel["case_ids"].split(","):
                    frequencies[cases_by_id[case_id]["support"]] += 1
            require(set(frequencies) == inventory, f"n={n}: incomplete support inventory")
            require(
                set(frequencies.values()) == {n},
                f"n={n}: cyclic panel support frequencies are not balanced",
            )


def request_for(panel: dict[str, str], cases_by_id: dict[str, dict[str, str]]) -> str:
    case_ids = panel["case_ids"].split(",")
    contexts = []
    for index, case_id in enumerate(case_ids, start=1):
        predicate = cases_by_id[case_id]["predicate"]
        field = CONTEXT_FIELDS[index - 1]
        contexts.append(f"{field}:[i:[HEAD:JOHN], ii:[HEAD:{predicate}]]")
    return f"H{len(case_ids)} [{', '.join(contexts)}]\n"


def expected_for(panel: dict[str, str], cases_by_id: dict[str, dict[str, str]]) -> str:
    return " ".join(
        run_benchmark.expected(cases_by_id[case_id])
        for case_id in panel["case_ids"].split(",")
    )


def metric_fields(metric_lines: list[str]) -> dict[str, str]:
    metric = run_benchmark.parse_metrics(metric_lines)
    return {
        output_name: metric.get(metric_name, "")
        for output_name, metric_name in METRIC_COLUMNS.items()
    }


def validate_result_row(row: dict[str, str]) -> None:
    n = int(row["n"])
    generated = int(row["unique_outputs"])
    valid = int(row["valid_outputs"])
    spurious = int(row["spurious_outputs"])
    expected_outputs = 1 if row["condition"] == "FULL" else 9**n
    require(int(row["expected_outputs"]) == expected_outputs, "incorrect expected-output formula")
    require(generated == expected_outputs, f"{row['condition']} {row['panel_id']}: output-count mismatch")
    require(valid == 1, f"{row['condition']} {row['panel_id']}: compatible output missing")
    require(spurious == generated - valid, f"{row['condition']} {row['panel_id']}: invalid output partition")


def write_results(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "condition", "panel_id", "n", "case_ids", "distinct_supports",
        "expected", "expected_outputs", "unique_outputs", "valid_outputs",
        "spurious_outputs", "valid_fraction", "wall_ms", "metric_lines",
        *METRIC_COLUMNS.keys(), "diagnostics",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=fields, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--elvex", help="path to the elvex executable")
    parser.add_argument("--cases", type=Path, default=HERE / "cases.tsv")
    parser.add_argument(
        "--panels", type=Path, default=HERE / "heterogeneous-panels.tsv"
    )
    parser.add_argument(
        "--output", type=Path, default=HERE / "heterogeneous-results.tsv"
    )
    parser.add_argument("--max-n", type=int, default=4)
    parser.add_argument(
        "--panels-per-n", type=int, default=0,
        help="run only the first K panels of each size (zero means all)",
    )
    parser.add_argument("--max-items", type=int, default=100000)
    parser.add_argument(
        "--conditions", default="FULL,NO-CONTEXT",
        help="comma-separated subset of FULL,NO-CONTEXT",
    )
    args = parser.parse_args()

    if not 1 <= args.max_n <= 4:
        parser.error("--max-n must be in 1..4")
    if args.panels_per_n < 0:
        parser.error("--panels-per-n must be non-negative")
    if args.max_items < 1:
        parser.error("--max-items must be positive")

    cases = read_tsv(args.cases)
    cases_by_id = {row["case_id"]: row for row in cases}
    panels = read_tsv(args.panels)
    validate_panels(
        panels,
        cases,
        balanced=args.panels.resolve() == (HERE / "heterogeneous-panels.tsv").resolve(),
    )
    selected_panels = []
    for n in range(1, args.max_n + 1):
        candidates = [panel for panel in panels if int(panel["n"]) == n]
        if args.panels_per_n:
            candidates = candidates[: args.panels_per_n]
        selected_panels.extend(candidates)
    require(selected_panels, "no heterogeneous panels selected")

    conditions = [value.strip() for value in args.conditions.split(",") if value.strip()]
    unknown = [value for value in conditions if value not in CONDITIONS]
    if unknown:
        parser.error(f"unknown conditions: {', '.join(unknown)}")

    elvex = run_benchmark.resolve_elvex(args.elvex)
    rows: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory(prefix="elvex-context-heterogeneous-") as directory:
        temporary = Path(directory)
        lexicon = temporary / "benchmark.lexicon"
        run_benchmark.write_lexicon(lexicon, cases)
        for condition in conditions:
            for panel in selected_panels:
                n = int(panel["n"])
                expected = expected_for(panel, cases_by_id)
                surfaces, metric_lines, wall_ms, diagnostics = run_benchmark.run_one(
                    elvex,
                    CONDITIONS[condition],
                    lexicon,
                    request_for(panel, cases_by_id),
                    temporary,
                    max_items=args.max_items,
                    metric_id=f"heterogeneous_{condition.lower()}_{panel['panel_id']}",
                )
                unique = {run_benchmark.normalize_surface(surface) for surface in surfaces}
                valid = int(run_benchmark.normalize_surface(expected) in unique)
                generated = len(unique)
                row = {
                    "condition": condition,
                    "panel_id": panel["panel_id"],
                    "n": str(n),
                    "case_ids": panel["case_ids"],
                    "distinct_supports": str(n),
                    "expected": expected,
                    "expected_outputs": str(1 if condition == "FULL" else 9**n),
                    "unique_outputs": str(generated),
                    "valid_outputs": str(valid),
                    "spurious_outputs": str(generated - valid),
                    "valid_fraction": f"{(valid / generated if generated else 0.0):.10f}",
                    "wall_ms": f"{wall_ms:.3f}",
                    "metric_lines": str(len(metric_lines)),
                    **metric_fields(metric_lines),
                    "diagnostics": diagnostics,
                }
                validate_result_row(row)
                rows.append(row)

    write_results(args.output, rows)
    grouped: dict[tuple[str, int], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["condition"], int(row["n"]))].append(row)

    print("condition\tN\tpanels\tgenerated\tvalid\tspurious\tvalid_%\twall_ms")
    for condition in conditions:
        for n in range(1, args.max_n + 1):
            selected = grouped[(condition, n)]
            if not selected:
                continue
            generated = sum(int(row["unique_outputs"]) for row in selected)
            valid = sum(int(row["valid_outputs"]) for row in selected)
            spurious = sum(int(row["spurious_outputs"]) for row in selected)
            wall_ms = sum(float(row["wall_ms"]) for row in selected)
            print(
                f"{condition}\t{n}\t{len(selected)}\t{generated}\t{valid}\t"
                f"{spurious}\t{100.0 * valid / generated:.6f}\t{wall_ms:.3f}"
            )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
