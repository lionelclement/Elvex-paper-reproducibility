#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.webnlg_utils import read_jsonl, write_jsonl


def parse_sizes(value: str) -> set[int]:
    try:
        sizes = {int(x.strip()) for x in value.split(",") if x.strip()}
    except ValueError as exc:
        raise argparse.ArgumentTypeError("sizes must be comma-separated integers") from exc
    if not sizes or min(sizes) < 1:
        raise argparse.ArgumentTypeError("sizes must contain positive integers")
    return sizes


def atomic_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Optional development view: one row per distinct observed triple.

    This view is deliberately *not* used by the paper benchmark because a
    lexicalisation of a multi-triple entry is not a gold reference for one of
    its component triples.
    """
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        for idx, triple in enumerate(row.get("triples", []), start=1):
            key = (triple.get("subject", ""), triple.get("predicate", ""), triple.get("object", ""))
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "id": f"{row.get('id', 'entry')}#t{idx}",
                "source_entry_id": row.get("id"),
                "source_file": row.get("source_file"),
                "category": row.get("category"),
                "split": row.get("split"),
                "size": 1,
                "triples": [triple],
                # Intentionally empty: the source sentence may express more
                # than this isolated triple and is therefore not a gold ref.
                "lexicalizations": [],
            })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Select official WebNLG entries by split and triple-set size")
    ap.add_argument("--triples", default=str(ROOT / "data/processed/triples.jsonl"))
    ap.add_argument("--out-dir", default=str(ROOT / "build/sequences"))
    ap.add_argument("--split", default="test", choices=["train", "dev", "test", "all"],
                    help="Benchmark split. Default: test")
    ap.add_argument("--sizes", type=parse_sizes, default=parse_sizes("1,2,3"),
                    help="Comma-separated official triple-set sizes. Default: 1,2,3")
    ap.add_argument("--atomic", action="store_true",
                    help="Development-only: replace size=1 by isolated distinct triples with no gold references")
    args = ap.parse_args()

    source_rows = list(read_jsonl(Path(args.triples)))
    rows = [r for r in source_rows if args.split == "all" or r.get("split") == args.split]

    groups: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        triples = row.get("triples", [])
        declared = int(row.get("size", len(triples)))
        if declared != len(triples):
            raise SystemExit(
                f"Entry {row.get('id')} has size={declared} but {len(triples)} extracted modified triples"
            )
        if declared in args.sizes:
            groups[declared].append(row)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    for size in sorted(args.sizes):
        dest = out / f"{size}.jsonl"
        selected = groups.get(size, [])
        if size == 1 and args.atomic:
            selected = atomic_rows(rows)
        n = write_jsonl(dest, selected)
        mode = "atomic development" if size == 1 and args.atomic else "official"
        print(f"{size} triple(s), {args.split} split, {mode}: {n} -> {dest}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
