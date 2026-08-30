#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().strip())


def value_forms(slot: str, value: Any) -> list[str]:
    v = str(value).strip()
    vl = v.lower()
    forms = {vl}

    if slot in {"familyFriendly", "kidsFriendly"}:
        if vl in {"yes", "true", "1"}:
            forms |= {
                "family-friendly", "family friendly", "kid-friendly", "kids friendly",
                "suitable for families", "suitable for children",
            }
        elif vl in {"no", "false", "0"}:
            forms |= {
                "not family-friendly", "not family friendly", "not kid-friendly",
                "not suitable for families", "not suitable for children", "no kids",
            }
    elif slot == "priceRange":
        if vl in {"cheap", "less than £20", "low"}:
            forms |= {
                "cheap", "low priced", "low-priced", "inexpensive",
                "less than £20", "less than 20",
            }
        elif vl in {"moderate", "£20-25", "20-25"}:
            forms |= {
                "moderate", "moderately priced", "mid-priced", "medium priced",
                "£20-25", "20-25",
            }
        elif vl in {"high", "more than £30", "expensive"}:
            forms |= {
                "high priced", "high-priced", "expensive", "more than £30", "more than 30",
            }
    elif slot == "customerRating":
        forms.add(vl.replace("/", " out of "))
        if vl in {"high", "average", "low"}:
            forms.add(f"{vl} customer rating")
        if re.fullmatch(r"\d\s*/\s*5", vl):
            forms.add(f"customer rating of {vl.replace('/', ' out of ')}")
    elif slot == "area":
        if vl == "riverside":
            forms |= {"riverside", "by the riverside", "by the river", "near the river"}
        elif vl in {"city centre", "city center"}:
            forms |= {"city centre", "city center", "centre of town", "center of town"}
    elif slot == "food":
        forms |= {vl, f"{vl} food", f"{vl} cuisine"}

    return sorted(forms, key=len, reverse=True)


def slot_present(text: str, slot: str, value: Any) -> bool:
    t = norm(text)
    return any(norm(form) in t for form in value_forms(slot, value))


def missing_slots_for_output(output: str, expected: dict[str, Any]) -> list[str]:
    return [slot for slot, value in expected.items() if not slot_present(output, slot, value)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outputs", required=True)
    ap.add_argument("--metrics", required=True)
    ap.add_argument("--details", default=None)
    ap.add_argument(
        "--all-outputs",
        action="store_true",
        help="Check every generated output; an item is valid only if every output is slot-complete.",
    )
    ap.add_argument(
        "--best-output",
        action="store_true",
        help="Select the generated output with the fewest omitted input slots.",
    )
    args = ap.parse_args()

    if args.all_outputs and args.best_output:
        raise SystemExit("Choose at most one of --all-outputs and --best-output")

    rows = [
        json.loads(line)
        for line in Path(args.outputs).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    total = len(rows)
    covered = 0
    valid_items = 0
    total_slots = 0
    omitted_slots = 0
    runtimes: list[float] = []
    outputs_per_item: list[int] = []
    outputs_evaluated = 0
    complete_outputs = 0
    details = []

    for row in rows:
        outputs = row.get("outputs", [])
        expected = row.get("expected_slots", {})
        generated = bool(row.get("ok") and outputs)
        if generated:
            covered += 1

        runtimes.append(float(row.get("runtime_ms") or 0.0))
        outputs_per_item.append(len(outputs))

        all_missing = [missing_slots_for_output(output, expected) for output in outputs]
        outputs_evaluated += len(all_missing)
        complete_outputs += sum(1 for missing in all_missing if not missing)

        if outputs:
            if args.best_output:
                best_index = min(range(len(outputs)), key=lambda i: (len(all_missing[i]), i))
                selected_outputs = [outputs[best_index]]
                selected_output_index = best_index
                missing_for_item = all_missing[best_index]
                item_valid = not missing_for_item
            elif args.all_outputs:
                selected_outputs = outputs
                selected_output_index = None
                missing_for_item = sorted({slot for missing in all_missing for slot in missing})
                item_valid = all(not missing for missing in all_missing)
            else:
                selected_outputs = outputs[:1]
                selected_output_index = 0
                missing_for_item = all_missing[0]
                item_valid = not missing_for_item
        else:
            selected_outputs = []
            selected_output_index = None
            missing_for_item = list(expected.keys())
            item_valid = False

        total_slots += len(expected)
        omitted_slots += len(missing_for_item)
        if item_valid:
            valid_items += 1

        details.append({
            "id": row.get("id"),
            "covered": generated,
            "valid": item_valid,
            "missing_slots": missing_for_item,
            "expected_slots": expected,
            "outputs": selected_outputs,
            "selected_output_index": selected_output_index,
            "all_outputs_count": len(outputs),
            "runtime_ms": row.get("runtime_ms"),
        })

    generated_output_counts = [n for n in outputs_per_item if n > 0]
    metrics = {
        "total_inputs": total,
        "generated_inputs": covered,
        "coverage": covered / total if total else 0.0,
        "item_validity": valid_items / total if total else 0.0,
        "slot_omission_rate": omitted_slots / total_slots if total_slots else 0.0,
        "slot_accuracy": 1.0 - (omitted_slots / total_slots) if total_slots else 0.0,
        "total_slots": total_slots,
        "omitted_slots": omitted_slots,
        "avg_outputs_per_input": sum(outputs_per_item) / total if total else 0.0,
        "avg_outputs_per_generated_input": (
            sum(generated_output_counts) / len(generated_output_counts)
            if generated_output_counts else 0.0
        ),
        "outputs_evaluated": outputs_evaluated,
        "complete_outputs": complete_outputs,
        "output_validity": (
            complete_outputs / outputs_evaluated if outputs_evaluated else 0.0
        ),
        "avg_runtime_ms": sum(runtimes) / total if total else 0.0,
        "mode": "best_output" if args.best_output else ("all_outputs" if args.all_outputs else "first_output"),
    }

    metrics_path = Path(args.metrics)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    if args.details:
        with Path(args.details).open("w", encoding="utf-8") as f:
            for detail in details:
                f.write(json.dumps(detail, ensure_ascii=False) + "\n")

    print(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
