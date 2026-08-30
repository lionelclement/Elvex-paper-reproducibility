#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.webnlg_utils import read_jsonl


EXPECTED_COUNTS = {
    ("dev", 1): 392, ("dev", 2): 302, ("dev", 3): 335,
    ("dev", 4): 312, ("dev", 5): 233, ("dev", 6): 23, ("dev", 7): 22,
    ("test", 1): 388, ("test", 2): 298, ("test", 3): 331,
    ("test", 4): 310, ("test", 5): 228, ("test", 6): 24, ("test", 7): 21,
    ("train", 1): 3115, ("train", 2): 2397, ("train", 3): 2662,
    ("train", 4): 2493, ("train", 5): 1851, ("train", 6): 188, ("train", 7): 170,
}
EXPECTED_TOTAL = 16095


def main() -> int:
    ap = argparse.ArgumentParser(description="Check invariants of the extracted WebNLG benchmark data")
    ap.add_argument("--triples", default=str(ROOT / "data/processed/triples.jsonl"))
    args = ap.parse_args()

    path = Path(args.triples)
    if not path.exists():
        raise SystemExit(f"Not found: {path}. Run ./run extract first.")

    rows = list(read_jsonl(path))
    errors: list[str] = []
    counts: Counter[tuple[str, int]] = Counter()
    seen: set[tuple[str, str]] = set()

    for row in rows:
        source = str(row.get("source_file", ""))
        split = str(row.get("split", "unknown"))
        triples = row.get("triples", [])
        size = int(row.get("size", len(triples)))
        key = (source, str(row.get("id", "")))

        if "release_v2.1" not in source or "/xml/" not in source.replace("\\", "/"):
            errors.append(f"unexpected source: {source}")
        if split not in {"train", "dev", "test"}:
            errors.append(f"unknown split for {key}: {split}")
        if size != len(triples):
            errors.append(f"size mismatch for {key}: declared {size}, extracted {len(triples)}")
        if key in seen:
            errors.append(f"duplicate entry identity: {key}")
        seen.add(key)
        counts[(split, size)] += 1

    if len(rows) != EXPECTED_TOTAL:
        errors.append(f"entry-count mismatch: found {len(rows)}, expected {EXPECTED_TOTAL}")
    if dict(counts) != EXPECTED_COUNTS:
        missing_or_changed = []
        for key in sorted(set(counts) | set(EXPECTED_COUNTS)):
            got = counts.get(key, 0)
            expected = EXPECTED_COUNTS.get(key, 0)
            if got != expected:
                missing_or_changed.append(f"{key[0]} size {key[1]}: found {got}, expected {expected}")
        errors.extend(missing_or_changed)

    print(f"Entries: {len(rows)}")
    print("split\tsize\tentries")
    for (split, size), n in sorted(counts.items()):
        print(f"{split}\t{size}\t{n}")

    if errors:
        print("\nERRORS", file=sys.stderr)
        for err in errors[:50]:
            print(f"- {err}", file=sys.stderr)
        if len(errors) > 50:
            print(f"- ... {len(errors) - 50} more", file=sys.stderr)
        return 1

    print("WebNLG extraction invariants: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
