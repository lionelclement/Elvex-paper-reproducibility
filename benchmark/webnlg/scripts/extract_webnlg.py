#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.webnlg_utils import parse_triple_text, write_jsonl


def relpath(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def local_name(tag: str) -> str:
    return tag.split("}", 1)[-1].lower()


def text_of(el: ET.Element) -> str:
    return "".join(el.itertext()).strip()


def infer_split(path: Path) -> str:
    parts = {p.lower() for p in path.parts}
    if "train" in parts:
        return "train"
    if "dev" in parts or "validation" in parts:
        return "dev"
    if "test" in parts:
        return "test"
    return "unknown"


def direct_children(entry: ET.Element, name: str) -> list[ET.Element]:
    wanted = name.lower()
    return [child for child in list(entry) if local_name(child.tag) == wanted]


def parse_entry(entry: ET.Element, path: Path, ordinal: int) -> dict[str, Any] | None:
    """Parse one official WebNLG XML entry.

    Only the *modified* triple set is used.  These are the triples presented to
    annotators and therefore the ones paired with the lexicalisations.  Original
    DBpedia triples and nested referring-expression <reference> annotations are
    deliberately ignored.
    """
    modified_sets = direct_children(entry, "modifiedtripleset")
    if not modified_sets:
        return None

    triples: list[dict[str, str]] = []
    for node in modified_sets[0]:
        if local_name(node.tag) != "mtriple":
            continue
        parsed = parse_triple_text(text_of(node))
        if parsed:
            triples.append({"subject": parsed[0], "predicate": parsed[1], "object": parsed[2]})

    if not triples:
        return None

    lexicalizations: list[str] = []
    for lex in direct_children(entry, "lex"):
        # In multilingual releases, keep English lexicalisations only.  v2.1
        # generally has no lang attribute, which is treated as English here.
        lang = (lex.attrib.get("lang") or "en").lower()
        if lang not in {"en", "eng", "english"}:
            continue

        # Some enriched WebNLG files put the sentence in a direct <text> child
        # and referring-expression annotations in nested <reference> nodes.
        # Only the full lexicalisation sentence is a gold reference.
        text_children = direct_children(lex, "text")
        if text_children:
            values = [text_of(node) for node in text_children]
        else:
            values = [(lex.text or "").strip()]
        lexicalizations.extend(value for value in values if value)

    declared_size = entry.attrib.get("size")
    size = int(declared_size) if str(declared_size).isdigit() else len(triples)
    if size != len(triples):
        raise ValueError(
            f"{path}: entry {entry.attrib.get('eid') or entry.attrib.get('id') or ordinal} "
            f"declares size={size} but contains {len(triples)} modified triples"
        )

    eid = entry.attrib.get("eid") or entry.attrib.get("id") or f"entry-{ordinal}"
    return {
        "id": str(eid),
        "source_file": relpath(path),
        "category": entry.attrib.get("category"),
        "split": infer_split(path),
        "size": size,
        "triples": triples,
        "lexicalizations": list(dict.fromkeys(lexicalizations)),
    }


def parse_xml(path: Path) -> list[dict[str, Any]]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"Cannot parse WebNLG XML {path}: {exc}") from exc

    rows: list[dict[str, Any]] = []
    ordinal = 0
    for entry in root.iter():
        if local_name(entry.tag) != "entry":
            continue
        ordinal += 1
        row = parse_entry(entry, path, ordinal)
        if row is not None:
            rows.append(row)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Extract official WebNLG modified RDF triples and lexicalisations from one XML release"
    )
    ap.add_argument(
        "--source-root",
        default=str(ROOT / "data/raw/webnlg-dataset-gitlab/release_v2.1/xml"),
        help="WebNLG XML release root. Default: official release_v2.1/xml",
    )
    ap.add_argument("--out", default=str(ROOT / "data/processed/triples.jsonl"))
    args = ap.parse_args()

    source_root = Path(args.source_root)
    if not source_root.exists():
        raise SystemExit(f"Not found: {source_root}. Run ./run download first.")

    files = sorted(p for p in source_root.rglob("*.xml") if "__MACOSX" not in p.parts)
    if not files:
        raise SystemExit(f"No XML files found below {source_root}")

    rows: list[dict[str, Any]] = []
    for path in files:
        rows.extend(parse_xml(path))

    # source_file + entry id is the stable identity.  The official XML tree may
    # reuse a short eid in different category/size files.
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda r: (r["split"], r["source_file"], r["id"])):
        key = (row["source_file"], row["id"])
        if key in seen:
            raise SystemExit(f"Duplicate WebNLG entry in selected XML release: {key}")
        seen.add(key)
        unique.append(row)

    n = write_jsonl(Path(args.out), unique)
    by_split: dict[str, int] = {}
    for row in unique:
        by_split[row["split"]] = by_split.get(row["split"], 0) + 1
    print(f"{n} official WebNLG entries written to {args.out}")
    print("Splits: " + ", ".join(f"{k}={v}" for k, v in sorted(by_split.items())))
    return 0 if n else 1


if __name__ == "__main__":
    raise SystemExit(main())
