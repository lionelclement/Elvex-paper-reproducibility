#!/usr/bin/env python3
"""Extract the lexical-context benchmark from Elvex/test/en-llm.

The benchmark deliberately uses a homogeneous syntactic frame so that the
ablation isolates lexical/contextual constraints rather than unrelated grammar
variation.  Cases are curated Oper1 support constructions that:
  * have an explicit predicative-noun profile;
  * use an indefinite nominal predicate;
  * realize a second semantic argument through a preposition;
  * have exactly one curated Oper1 support realization for the predicate.

The resulting snapshot is committed in this repository.  --check verifies that
it still matches a local Elvex checkout.
"""
from __future__ import annotations

import argparse
import csv
import io
from collections import Counter
from pathlib import Path

FIELDS = [
    "case_id", "predicate", "noun", "support", "verb", "article", "prep",
    "arg2_class", "pred_class", "aktionsart", "semantic_valency", "fixedness",
    "support_aspect", "support_phase", "support_stance",
    "support_subjectivity", "support_register",
]

# END is intentionally excluded because it is a poor benchmark lexical head and
# can also be confused with implementation-level end markers in some tools.
EXCLUDED_PREDICATES = {"END"}


def read_tsv(path: Path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def morph_index(path: Path):
    rows = []
    with path.open(encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if not line or line.startswith("//"):
                continue
            parts = line.split("\t")
            if len(parts) != 4:
                continue
            form, pos, lemma, features = parts
            rows.append((form, pos, lemma, features))
    return rows


def noun_form(morph, lemma: str) -> str:
    for form, pos, got_lemma, features in morph:
        if pos == "common_noun" and got_lemma == lemma and "@s" in features:
            return form
    raise ValueError(f"no singular common_noun morphology for {lemma}")


def verb_3sg(morph, lemma: str) -> str:
    for form, pos, got_lemma, features in morph:
        if (
            pos == "verb" and got_lemma == lemma
            and "vtense:present" in features and "@_3s" in features
        ):
            return form
    raise ValueError(f"no present 3sg verb morphology for {lemma}")


def extract(elvex_root: Path):
    root = elvex_root / "test" / "en-llm"
    lf = read_tsv(root / "en-lexical-functions.tsv")
    pred_profiles = {
        row["predicate"]: row for row in read_tsv(root / "en-predicative-nouns.tsv")
    }
    support_profiles = {
        row["realizer"]: row for row in read_tsv(root / "en-support-verb-profiles.tsv")
    }
    morph = morph_index(root / "en.morpho")

    eligible = [
        row for row in lf
        if row["kind"] == "support"
        and row["function"] == "oper1"
        and row["form"] == "indef"
        and row["prep"]
        and row["predicate"] in pred_profiles
        and row["predicate"] not in EXCLUDED_PREDICATES
    ]
    multiplicity = Counter((row["predicate"], row["function"]) for row in eligible)
    eligible = [
        row for row in eligible
        if multiplicity[(row["predicate"], row["function"])] == 1
    ]

    out = []
    for row in eligible:
        predicate = row["predicate"]
        support = row["realizer"]
        pred = pred_profiles[predicate]
        spr = support_profiles[support]
        noun = noun_form(morph, predicate)
        # a/an is intentionally outside the grammar under test (as in en-llm);
        # keep only consonant-initial nouns so a fixed indefinite article is grammatical.
        if noun[:1].lower() in "aeiou":
            continue
        article = "a"
        arg2 = pred["arg2_restriction"]
        if arg2 not in {"human", "entity", "event", "institution", "location"}:
            raise ValueError(f"unsupported arg2 class {arg2!r} for {predicate}")
        out.append({
            "case_id": "",
            "predicate": predicate,
            "noun": noun,
            "support": support,
            "verb": verb_3sg(morph, support),
            "article": article,
            "prep": row["prep"],
            "arg2_class": arg2,
            "pred_class": pred["class"],
            "aktionsart": pred["aktionsart"],
            "semantic_valency": pred["semantic_valency"],
            "fixedness": pred["fixedness"],
            "support_aspect": spr["lexical_aspect"],
            "support_phase": spr["phase"],
            "support_stance": spr["stance"],
            "support_subjectivity": spr["subjectivity"],
            "support_register": spr["register"],
        })
    for i, row in enumerate(out, 1):
        row["case_id"] = f"L{i:02d}"
    return out


def render(rows) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--elvex-root", type=Path, default=Path("../Elvex"))
    ap.add_argument("--output", type=Path, default=Path(__file__).with_name("cases.tsv"))
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    text = render(extract(args.elvex_root.resolve()))
    if args.check:
        current = args.output.read_text(encoding="utf-8")
        if current != text:
            raise SystemExit("cases.tsv is out of date; rerun extract_cases.py")
        print(f"OK: {text.count(chr(10)) - 1} lexical-context cases")
        return
    args.output.write_text(text, encoding="utf-8")
    print(f"wrote {args.output}: {text.count(chr(10)) - 1} cases")


if __name__ == "__main__":
    main()
