from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rerun = load_module("rerun_e2e_gem", ROOT / "rerun_e2e_gem.py")
inputs = load_module("make_full_e2e_inputs", ROOT / "scripts" / "make_full_e2e_inputs.py")


class E2EPipelineTests(unittest.TestCase):
    def test_all_gem_references_are_preserved(self):
        row = {
            "target": "Reference A",
            "references": ["Reference A", "Reference B", "Reference C"],
        }
        self.assertEqual(
            rerun.get_references(row),
            ["Reference A", "Reference B", "Reference C"],
        )

    def test_slot_signature_is_exact_and_ordered(self):
        slots = {"food": "Italian", "name": "Aromi", "area": "riverside"}
        self.assertEqual(inputs.slot_signature(slots), "name|food|area")
        fs = inputs.slots_to_features(slots, "DESCRIBE_RESTAURANT")
        self.assertEqual(fs["slotset"], "name|food|area")

    def test_train_only_lexicon_coverage_reports_unseen_test_value(self):
        train = [{
            "fragment_id": "train-1",
            "expected_slots": {"name": "Aromi", "food": "Italian"},
        }]
        test = [
            {
                "fragment_id": "test-1",
                "expected_slots": {"name": "Aromi", "food": "Italian"},
            },
            {
                "fragment_id": "test-2",
                "expected_slots": {"name": "New Place", "food": "Italian"},
            },
        ]
        report = rerun.lexicon_coverage_report(train, test)
        self.assertFalse(report["all_test_values_seen_in_train"])
        self.assertEqual(report["missing_test_values"], {"name": ["New Place"]})
        self.assertEqual(report["test_inputs_with_unseen_values"], 1)

    def test_generated_grammar_uses_slotset_and_train_lexicon_only(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            train_items = td / "train.jsonl"
            train_items.write_text(
                json.dumps({
                    "expected_slots": {
                        "name": "Aromi",
                        "food": "Italian",
                        "area": "riverside",
                    }
                }) + "\n",
                encoding="utf-8",
            )
            rules = td / "e2e.rules"
            lexicon = td / "e2e.lexicon"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_full_e2e_grammar.py"),
                    "--lexicon-items", str(train_items),
                    "--rules-out", str(rules),
                    "--lexicon-out", str(lexicon),
                ],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )
            rules_text = rules.read_text(encoding="utf-8")
            lexicon_text = lexicon.read_text(encoding="utf-8")
            self.assertIn('slotset:"name|food|area"', rules_text)
            self.assertIn('"Aromi" name [name:"Aromi"]', lexicon_text)
            self.assertNotIn("New Place", lexicon_text)
            # Named and unnamed inputs must not share the same subject nonterminal:
            # otherwise a named MR can license ``The restaurant`` and an unnamed
            # MR can license every restaurant name in the training lexicon.
            self.assertIn("NAMED_SUBJECT → name", rules_text)
            self.assertIn("GENERIC_SUBJECT → generic_subject", rules_text)
            rule_lines = rules_text.splitlines()
            self.assertNotIn("SUBJECT → name { ↓1 = ↑; ⇑ = ⇓1; }", rule_lines)
            self.assertNotIn("SUBJECT → generic_subject { ↓1 = ↑; ⇑ = ⇓1; }", rule_lines)
            self.assertIn("RestaurantDescription → NAMED_SUBJECT", rules_text)
            self.assertIn("RestaurantDescription → GENERIC_SUBJECT", rules_text)

    def test_direct_csv_source_loader(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            source = td / "train.csv"
            source.write_text(
                'mr,ref\n"name[Aromi], food[Italian]","Aromi serves Italian food."\n',
                encoding="utf-8",
            )
            old = rerun.E2E_SOURCES["train"]
            rerun.E2E_SOURCES["train"] = {
                "filename": source.name,
                "format": "csv",
                "url": source.as_uri(),
                "sha256": rerun.sha256_file(source),
            }
            try:
                rows = rerun.load_e2e_source("train", td)
            finally:
                rerun.E2E_SOURCES["train"] = old
            self.assertEqual(rows[0]["mr"], "name[Aromi], food[Italian]")
            self.assertEqual(rows[0]["ref"], "Aromi serves Italian food.")

    def test_direct_gem_json_source_loader_preserves_references(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            source = td / "test.json"
            source.write_text(
                json.dumps([{
                    "meaning_representation": "name[Aromi], food[Italian]",
                    "references": ["Reference A", "Reference B"],
                }]),
                encoding="utf-8",
            )
            old = rerun.E2E_SOURCES["test"]
            rerun.E2E_SOURCES["test"] = {
                "filename": source.name,
                "format": "gem-json",
                "url": source.as_uri(),
                "sha256": rerun.sha256_file(source),
            }
            try:
                rows = rerun.load_e2e_source("test", td)
            finally:
                rerun.E2E_SOURCES["test"] = old
            self.assertEqual(rows[0]["target"], "Reference A")
            self.assertEqual(rows[0]["references"], ["Reference A", "Reference B"])


if __name__ == "__main__":
    unittest.main()
