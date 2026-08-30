from __future__ import annotations

import importlib.util
import json
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


extract = load_module("extract_webnlg", ROOT / "scripts/extract_webnlg.py")
select = load_module("select_sequences", ROOT / "scripts/select_sequences.py")
generate = load_module("generate_inputs", ROOT / "scripts/generate_inputs.py")


XML = """<?xml version='1.0' encoding='UTF-8'?>
<benchmark>
  <entries>
    <entry category="Food" eid="Id65" size="2">
      <originaltripleset>
        <otriple>Old_subject | oldPredicate | Old_object</otriple>
      </originaltripleset>
      <modifiedtripleset>
        <mtriple>Arros_negre | country | Spain</mtriple>
        <mtriple>Arros_negre | ingredient | White_rice</mtriple>
      </modifiedtripleset>
      <lex comment="good" lid="1">White rice is an ingredient of Arros negre from Spain.
        <references>
          <reference entity="Arros_negre">Arros negre</reference>
        </references>
      </lex>
      <lex comment="good" lid="2">Arros negre contains white rice and comes from Spain.</lex>
    </entry>
  </entries>
</benchmark>
"""


class WebNLGIngestionTests(unittest.TestCase):
    def test_xml_uses_modified_triples_only_and_direct_lex_text(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "release_v2.1" / "xml" / "test" / "2triples" / "Food.xml"
            path.parent.mkdir(parents=True)
            path.write_text(XML, encoding="utf-8")
            rows = extract.parse_xml(path)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["split"], "test")
        self.assertEqual(row["size"], 2)
        self.assertEqual(
            row["triples"],
            [
                {"subject": "Arros_negre", "predicate": "country", "object": "Spain"},
                {"subject": "Arros_negre", "predicate": "ingredient", "object": "White_rice"},
            ],
        )
        self.assertNotIn("oldPredicate", json.dumps(row["triples"]))
        self.assertEqual(
            row["lexicalizations"],
            [
                "White rice is an ingredient of Arros negre from Spain.",
                "Arros negre contains white rice and comes from Spain.",
            ],
        )

    def test_input_generation_preserves_official_triple_count(self):
        row = {
            "triples": [
                {"subject": "A", "predicate": "p", "object": "B"},
                {"subject": "A", "predicate": "p", "object": "B"},
            ]
        }
        text = generate.fs_for_row(row, {}, set())
        self.assertIn("size:2", text)
        self.assertIn("i:[", text)
        self.assertIn("ii:[", text)

    def test_atomic_development_rows_have_no_gold_references(self):
        rows = [{
            "id": "Id65",
            "source_file": "release_v2.1/xml/test/2triples/Food.xml",
            "category": "Food",
            "split": "test",
            "size": 2,
            "triples": [
                {"subject": "A", "predicate": "p", "object": "B"},
                {"subject": "A", "predicate": "q", "object": "C"},
            ],
            "lexicalizations": ["A sentence expressing both facts."],
        }]
        atomic = select.atomic_rows(rows)
        self.assertEqual(len(atomic), 2)
        self.assertTrue(all(r["size"] == 1 for r in atomic))
        self.assertTrue(all(r["lexicalizations"] == [] for r in atomic))


if __name__ == "__main__":
    unittest.main()
