#!/usr/bin/env python3

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUN = ROOT / "runs" / "full"

EXPECTED_INPUTS = 1847
EXPECTED_SLOTS = 11428
EXPECTED_REFERENCES = 4693

errors = []
warnings = []


def load_json(path):
    if not path.exists():
        errors.append(f"missing file: {path.relative_to(ROOT)}")
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        errors.append(f"cannot read {path.relative_to(ROOT)}: {e}")
        return {}


def pct(x):
    return f"{100.0 * x:.1f}%"


def check_equal(label, got, expected):
    if got == expected:
        print(f"OK   {label}: {got}")
    else:
        print(f"FAIL {label}: {got} (expected {expected})")
        errors.append(f"{label}: {got} != {expected}")


def check_close(label, got, expected, eps=1e-9):
    if got is not None and math.isclose(got, expected, abs_tol=eps):
        print(f"OK   {label}: {got}")
    else:
        print(f"FAIL {label}: {got} (expected {expected})")
        errors.append(f"{label}: {got} != {expected}")


print("=== E2E/GEM dataset ===")

summary = load_json(RUN / "dataset_summary.json")

check_equal("inputs", summary.get("inputs"), EXPECTED_INPUTS)
check_equal("slots", summary.get("total_slots"), EXPECTED_SLOTS)
check_equal("references", summary.get("references"), EXPECTED_REFERENCES)

print()
print("=== Train/test lexical separation ===")

coverage = load_json(RUN / "lexicon_coverage.json")

check_equal(
    "lexicon source split",
    coverage.get("lexicon_source_split"),
    "train",
)
check_equal(
    "evaluation split",
    coverage.get("evaluation_split"),
    "test",
)
check_equal(
    "test inputs with unseen values",
    coverage.get("test_inputs_with_unseen_values"),
    0,
)
check_equal(
    "all test values seen in train",
    coverage.get("all_test_values_seen_in_train"),
    True,
)

print()
print("=== Elvex run ===")

outputs_path = RUN / "outputs_test_all.jsonl"

rows = []
if not outputs_path.exists():
    errors.append(
        f"missing file: {outputs_path.relative_to(ROOT)} "
        "(generation has probably not completed)"
    )
else:
    with outputs_path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))

if rows:
    check_equal("evaluated inputs", len(rows), EXPECTED_INPUTS)

    process_ok = sum(bool(r.get("ok")) for r in rows)
    process_failed = len(rows) - process_ok
    generated = sum(bool(r.get("ok")) and bool(r.get("outputs")) for r in rows)
    total_outputs = sum(len(r.get("outputs", [])) for r in rows)

    print(f"OK   process successful: {process_ok}/{len(rows)}")
    print(f"INFO process failed:     {process_failed}")
    print(f"INFO generated inputs:   {generated}/{len(rows)} "
          f"({100.0 * generated / len(rows):.1f}%)")
    print(f"INFO total outputs:      {total_outputs}")
    print(f"INFO mean outputs/input: {total_outputs / len(rows):.2f}")

    if process_failed:
        errors.append(f"{process_failed} Elvex process(es) failed")
        print()
        print("Failed inputs:")
        for r in rows:
            if not r.get("ok"):
                print(
                    f"  {r.get('id')}: returncode={r.get('returncode')} "
                    f"stderr={str(r.get('stderr', '')).strip()[:160]}"
                )

    generated_fraction = generated / len(rows)
    mean_outputs = total_outputs / len(rows)
else:
    generated_fraction = None
    mean_outputs = None


def show_metrics(title, filename):
    path = RUN / filename
    if not path.exists():
        print()
        print(f"--- {title} ---")
        print(f"MISSING {filename}")
        warnings.append(f"{filename} not found")
        return None

    m = load_json(path)

    print()
    print(f"--- {title} ---")
    print(f"Mode:          {m.get('mode')}")
    print(f"Inputs:        {m.get('total_inputs')}")
    print(f"Coverage:      {pct(m.get('coverage', 0.0))}")
    print(f"Slots:         {m.get('total_slots')}")
    print(f"Slot accuracy: {pct(m.get('slot_accuracy', 0.0))}")
    print(f"SER:           {pct(m.get('slot_omission_rate', 0.0))}")
    print(f"Item validity: {pct(m.get('item_validity', 0.0))}")
    print(f"Outputs/input: {m.get('avg_outputs_per_input', 0.0):.2f}")
    print(f"Omitted slots: {m.get('omitted_slots')}")

    check_equal(
        f"{title}: total inputs",
        m.get("total_inputs"),
        EXPECTED_INPUTS,
    )
    check_equal(
        f"{title}: total slots",
        m.get("total_slots"),
        EXPECTED_SLOTS,
    )

    if generated_fraction is not None:
        check_close(
            f"{title}: coverage agrees with raw output",
            m.get("coverage"),
            generated_fraction,
        )

    if mean_outputs is not None:
        check_close(
            f"{title}: mean outputs agrees with raw output",
            m.get("avg_outputs_per_input"),
            mean_outputs,
        )

    return m


print()
print("=== Slot-preservation metrics ===")

first = show_metrics("First output", "metrics_first_output.json")
best = show_metrics("Best in forest", "metrics_best_in_forest.json")
all_outputs = show_metrics("All outputs", "metrics_all_outputs.json")

print()
print("=== Scientific checks ===")

if first:
    if first.get("slot_omission_rate") == 0:
        print("OK   first output preserves every input slot")
    else:
        print(
            "WARN first output omits slots: "
            f"SER={pct(first.get('slot_omission_rate', 0.0))}"
        )

if best:
    if best.get("slot_omission_rate") == 0:
        print("OK   best-in-forest preserves every input slot")
    else:
        print(
            "WARN best-in-forest still omits slots: "
            f"SER={pct(best.get('slot_omission_rate', 0.0))}"
        )

if all_outputs:
    if (
        all_outputs.get("slot_omission_rate") == 0
        and all_outputs.get("slot_accuracy") == 1.0
    ):
        print("OK   every generated realization is slot-complete")
    else:
        print(
            "FAIL not every generated realization is slot-complete: "
            f"Acc={pct(all_outputs.get('slot_accuracy', 0.0))}, "
            f"SER={pct(all_outputs.get('slot_omission_rate', 0.0))}"
        )
        errors.append("some generated realizations omit input slots")

print()
print("=== Result ===")

if errors:
    print("FAILED")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)

if warnings:
    print("OK, with warnings")
    for w in warnings:
        print(f"  - {w}")
else:
    print("OK: benchmark output is internally consistent")
