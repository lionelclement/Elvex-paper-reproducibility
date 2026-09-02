from __future__ import annotations

import copy
import re
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import check_results  # noqa: E402
import check_heterogeneous_results  # noqa: E402
import run_benchmark  # noqa: E402
import run_heterogeneous  # noqa: E402
import run_repeated  # noqa: E402


class LexicalContextSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = check_results.read_tsv(HERE / "cases.tsv")
        cls.results = check_results.read_tsv(HERE / "reference-results.tsv")

    def test_committed_snapshot(self):
        summary = check_results.validate_rows(self.cases, self.results)
        self.assertEqual(summary["FULL"]["valid"], 12)
        self.assertEqual(summary["PRE-SPECIFIED"]["valid"], 12)
        self.assertEqual(summary["NO-CONTEXT"]["generated"], 108)
        self.assertEqual(summary["NO-CONTEXT"]["spurious"], 96)

    def test_snapshot_has_independent_lexical_variety(self):
        self.assertEqual(len(self.cases), 12)
        self.assertEqual(len({row["support"] for row in self.cases}), 9)
        self.assertGreaterEqual(len({row["pred_class"] for row in self.cases}), 6)
        self.assertGreaterEqual(len({row["prep"] for row in self.cases}), 4)

    def test_no_context_enumerates_exactly_the_fixed_support_inventory(self):
        source = (HERE / "no-context.rules").read_text(encoding="utf-8")
        enumerated = set(re.findall(r"↓1\s*=\s*\[HEAD:([A-Z_]+)\]", source))
        expected = {row["support"] for row in self.cases}
        self.assertEqual(enumerated, expected)
        self.assertEqual(source.count("VP → V Det N"), len(expected))

    def test_full_and_prespecified_keep_the_same_surface_topology(self):
        full = (HERE / "full.rules").read_text(encoding="utf-8")
        prespecified = (HERE / "pre-specified.rules").read_text(encoding="utf-8")
        self.assertEqual(full.count("VP → V Det N"), 1)
        self.assertEqual(prespecified.count("VP → V Det N"), 1)
        self.assertIn("deferred (⇓3)", full)
        self.assertIn("[support:$support] ⊂ ⇓3", full)
        self.assertIn("↓1 = $support", full)
        self.assertIn("support:$support", prespecified)

    def test_generated_lexicon_preserves_every_curated_mapping(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            path = Path(directory) / "generated.lexicon"
            run_benchmark.write_lexicon(path, self.cases)
            source = path.read_text(encoding="utf-8")
        for row in self.cases:
            self.assertIn(f'HEAD:{row["predicate"]},', source)
            self.assertIn(f'support:[HEAD:{row["support"]}]', source)
            self.assertIn(f'HEAD:{row["support"]},', source)

    def test_checker_rejects_a_hidden_full_overgeneration(self):
        changed = copy.deepcopy(self.results)
        row = next(row for row in changed if row["condition"] == "FULL")
        row["unique_outputs"] = "2"
        row["spurious_outputs"] = "1"
        row["valid_fraction"] = "0.50000000"
        with self.assertRaisesRegex(ValueError, "expected one valid output only"):
            check_results.validate_rows(self.cases, changed)

    def test_checker_rejects_loss_of_gold_under_ablation(self):
        changed = copy.deepcopy(self.results)
        row = next(row for row in changed if row["condition"] == "NO-CONTEXT")
        row["valid_outputs"] = "0"
        row["spurious_outputs"] = "9"
        row["valid_fraction"] = "0.00000000"
        with self.assertRaisesRegex(ValueError, "expected one valid output"):
            check_results.validate_rows(self.cases, changed)

    def test_heterogeneous_panels_are_balanced_and_non_redundant(self):
        panels = run_heterogeneous.read_tsv(HERE / "heterogeneous-panels.tsv")
        run_heterogeneous.validate_panels(panels, self.cases, balanced=True)
        self.assertEqual(len(panels), 36)
        for n in range(1, 5):
            selected = [panel for panel in panels if int(panel["n"]) == n]
            self.assertEqual(len(selected), 9)

    def test_heterogeneous_requests_preserve_distinct_case_inputs(self):
        panels = run_heterogeneous.read_tsv(HERE / "heterogeneous-panels.tsv")
        cases_by_id = {row["case_id"]: row for row in self.cases}
        panel = next(panel for panel in panels if panel["panel_id"] == "N4-P01")
        request = run_heterogeneous.request_for(panel, cases_by_id)
        self.assertTrue(request.startswith("H4 ["))
        for case_id in panel["case_ids"].split(","):
            self.assertIn(f"HEAD:{cases_by_id[case_id]['predicate']}", request)

    def test_heterogeneous_grammars_isolate_the_context_intervention(self):
        full = (HERE / "heterogeneous-full.rules").read_text(encoding="utf-8")
        no_context = (HERE / "heterogeneous-no-context.rules").read_text(encoding="utf-8")
        for n in range(1, 5):
            self.assertIn(f"H{n} →", full)
            self.assertIn(f"H{n} →", no_context)
        self.assertIn("deferred (⇓3)", full)
        self.assertIn("[support:$support] ⊂ ⇓3", full)
        self.assertNotIn("[support:$support] ⊂ ⇓3", no_context)
        enumerated = set(re.findall(r"↓1\s*=\s*\[HEAD:([A-Z_]+)\]", no_context))
        self.assertEqual(enumerated, {row["support"] for row in self.cases})

    def test_heterogeneous_checker_accepts_exact_formulas(self):
        panels = run_heterogeneous.read_tsv(HERE / "heterogeneous-panels.tsv")
        rows = []
        for condition in ("FULL", "NO-CONTEXT"):
            for panel in panels:
                n = int(panel["n"])
                generated = 1 if condition == "FULL" else 9**n
                rows.append({
                    "condition": condition,
                    "panel_id": panel["panel_id"],
                    "n": panel["n"],
                    "case_ids": panel["case_ids"],
                    "expected_outputs": str(generated),
                    "unique_outputs": str(generated),
                    "valid_outputs": "1",
                    "spurious_outputs": str(generated - 1),
                })
        check_heterogeneous_results.validate(rows, panels, complete=True)

    def test_repeated_timing_summary_uses_distribution_statistics(self):
        rows = []
        for condition in run_repeated.CONDITIONS:
            for repeat, value in enumerate((10.0, 20.0, 30.0, 40.0), start=1):
                rows.append({
                    "repeat": str(repeat),
                    "condition": condition,
                    "wall_ms": str(value),
                })
        summary = {row["condition"]: row for row in run_repeated.summarize(rows)}
        self.assertEqual(summary["FULL"]["runs"], "4")
        self.assertEqual(summary["FULL"]["median_ms"], "25.000")
        self.assertEqual(summary["FULL"]["q1_ms"], "17.500")
        self.assertEqual(summary["FULL"]["q3_ms"], "32.500")
        self.assertEqual(summary["FULL"]["iqr_ms"], "15.000")

    def test_repeated_runner_balances_all_condition_orders(self):
        self.assertEqual(len(run_repeated.CONDITION_ORDERS), 6)
        first_positions = [order[0] for order in run_repeated.CONDITION_ORDERS]
        self.assertEqual(first_positions.count("FULL"), 2)
        self.assertEqual(first_positions.count("NO-CONTEXT"), 2)
        self.assertEqual(first_positions.count("PRE-SPECIFIED"), 2)


if __name__ == "__main__":
    unittest.main()
