#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
import json
import re
from pathlib import Path
from typing import Any

CONTENT_SLOTS = ["eatType", "food", "priceRange", "area", "near", "familyFriendly", "customerRating"]
SIGNATURE_ORDER = ["name", *CONTENT_SLOTS]
VAR_FOR_SLOT = {
    "eatType": "EatType",
    "food": "Food",
    "priceRange": "Price",
    "area": "Area",
    "near": "Near",
    "familyFriendly": "Family",
    "customerRating": "Rating",
}
NT_FOR_SLOT = {
    "eatType": "EATTYPE_CLAUSE",
    "food": "FOOD_CLAUSE",
    "priceRange": "PRICE_CLAUSE",
    "area": "AREA_CLAUSE",
    "near": "NEAR_CLAUSE",
    "familyFriendly": "FAMILY_CLAUSE",
    "customerRating": "RATING_CLAUSE",
}
VALUE_CAT_FOR_SLOT = {
    "eatType": "eat_type_value",
    "food": "food_value",
    "priceRange": "price_value",
    "area": "area_value",
    "near": "near_value",
    "familyFriendly": "family_value",
    "customerRating": "rating_value",
}


def q(s: Any) -> str:
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def clean_value(s: Any) -> str:
    s = str(s).replace("_", " ").strip()
    s = re.sub(r"\s+", " ", s)
    if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
        s = s[1:-1].strip()
    return s


def slot_signature(has_name: bool, subset: tuple[str, ...]) -> str:
    present = ({"name"} if has_name else set()) | set(subset)
    return "|".join(slot for slot in SIGNATURE_ORDER if slot in present)


def value_surface(slot: str, value: Any) -> str:
    v = clean_value(value)
    vl = v.lower()

    if slot == "eatType":
        if vl in {"pub", "restaurant"}:
            return "a " + vl
        if vl == "coffee shop":
            return "a coffee shop"
        return v

    if slot == "food":
        return v if vl.endswith("food") else f"{v} food"

    if slot == "priceRange":
        if vl == "cheap":
            return "cheap"
        if vl == "moderate":
            return "moderately priced"
        if vl == "high":
            return "high priced"
        return v

    if slot == "area":
        if vl in {"city centre", "city center"}:
            return "in the city centre"
        if vl == "riverside":
            return "by the riverside"
        return "in " + v

    if slot == "near":
        return "near " + v

    if slot == "familyFriendly":
        if vl in {"yes", "true", "1"}:
            return "family-friendly"
        if vl in {"no", "false", "0"}:
            return "not family-friendly"
        return v

    if slot == "customerRating":
        if vl == "high":
            return "a high customer rating"
        if vl == "average":
            return "an average customer rating"
        if vl == "low":
            return "a low customer rating"
        return f"a customer rating of {v}"

    return v


def read_items(path: Path):
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def write_rules(path: Path) -> None:
    lines: list[str] = [
        "/************************************************************",
        "* E2E closed-domain realization grammar.",
        "* Every RestaurantDescription rule carries an exact slotset guard.",
        "* This prevents a rule for a slot subset from matching a richer MR.",
        "************************************************************/",
        "",
        "@withoutSpaces",
        "Axiom → RestaurantDescription {",
        "  ↓1 = ↑;",
        "  ⇑ = ⇓1;",
        "}",
        "",
    ]

    for has_name in (True, False):
        for r in range(0, len(CONTENT_SLOTS) + 1):
            for subset in itertools.combinations(CONTENT_SLOTS, r):
                if not has_name and not subset:
                    continue

                signature = slot_signature(has_name, subset)
                rhs = ["NAMED_SUBJECT" if has_name else "GENERIC_SUBJECT"]
                for i, slot in enumerate(subset):
                    if i > 0:
                        rhs.append("COORD")
                    rhs.append(NT_FOR_SLOT[slot])

                label = "name" if has_name else "generic subject"
                lines += ["", f"/*** {label} + {','.join(subset) or 'no content slot'} ***/"]
                lines.append("RestaurantDescription → " + " ".join(rhs) + " {")
                lines.append("  [HEAD:DESCRIBE_RESTAURANT,")
                feature_lines = [f"   slotset:{q(signature)}"]
                if has_name:
                    feature_lines.append("   name:$Name")
                for slot in subset:
                    feature_lines.append(f"   {slot}:${VAR_FOR_SLOT[slot]}")
                for i, feature_line in enumerate(feature_lines):
                    comma = "," if i < len(feature_lines) - 1 else ""
                    lines.append(feature_line + comma)
                lines.append("  ];")
                lines.append("")

                lines.append("  ↓1 = [name:$Name];" if has_name else "  ↓1 = [];")
                pos = 2
                for i, slot in enumerate(subset):
                    if i > 0:
                        lines.append(f"  ↓{pos} = [];")
                        pos += 1
                    lines.append(f"  ↓{pos} = [{slot}:${VAR_FOR_SLOT[slot]}];")
                    pos += 1
                lines.append("")
                lines.append("  ⇑ = ↑;")
                lines.append("}")

    lines += [
        "",
        "/************************************************************",
        "* Slot-specific clauses",
        "************************************************************/",
        "",
        "NAMED_SUBJECT → name { ↓1 = ↑; ⇑ = ⇓1; }",
        "GENERIC_SUBJECT → generic_subject { ↓1 = ↑; ⇑ = ⇓1; }",
        "",
        "EATTYPE_CLAUSE → copula EATTYPE_VALUE {",
        "  [eatType:$Value];",
        "  ↓1 = [];",
        "  ↓2 = [eatType:$Value];",
        "  ⇑ = ↑;",
        "}",
        "",
        "FOOD_CLAUSE → serve_marker FOOD_VALUE {",
        "  [food:$Value];",
        "  ↓1 = [];",
        "  ↓2 = [food:$Value];",
        "  ⇑ = ↑;",
        "}",
        "",
        "PRICE_CLAUSE → copula PRICE_VALUE {",
        "  [priceRange:$Value];",
        "  ↓1 = [];",
        "  ↓2 = [priceRange:$Value];",
        "  ⇑ = ↑;",
        "}",
        "",
        "AREA_CLAUSE → copula AREA_VALUE {",
        "  [area:$Value];",
        "  ↓1 = [];",
        "  ↓2 = [area:$Value];",
        "  ⇑ = ↑;",
        "}",
        "",
        "NEAR_CLAUSE → NEAR_VALUE {",
        "  [near:$Value];",
        "  ↓1 = [near:$Value];",
        "  ⇑ = ↑;",
        "}",
        "",
        "FAMILY_CLAUSE → copula FAMILY_VALUE {",
        "  [familyFriendly:$Value];",
        "  ↓1 = [];",
        "  ↓2 = [familyFriendly:$Value];",
        "  ⇑ = ↑;",
        "}",
        "",
        "RATING_CLAUSE → have_marker RATING_VALUE {",
        "  [customerRating:$Value];",
        "  ↓1 = [];",
        "  ↓2 = [customerRating:$Value];",
        "  ⇑ = ↑;",
        "}",
        "",
        "EATTYPE_VALUE → eat_type_value { ↓1 = ↑; ⇑ = ⇓1; }",
        "FOOD_VALUE → food_value { ↓1 = ↑; ⇑ = ⇓1; }",
        "PRICE_VALUE → price_value { ↓1 = ↑; ⇑ = ⇓1; }",
        "AREA_VALUE → area_value { ↓1 = ↑; ⇑ = ⇓1; }",
        "NEAR_VALUE → near_value { ↓1 = ↑; ⇑ = ⇓1; }",
        "FAMILY_VALUE → family_value { ↓1 = ↑; ⇑ = ⇓1; }",
        "RATING_VALUE → rating_value { ↓1 = ↑; ⇑ = ⇓1; }",
        "COORD → coord { ↓1 = ↑; ⇑ = ⇓1; }",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--lexicon-items",
        required=True,
        help="JSONL items used only to construct the lexical inventory (train split in the benchmark).",
    )
    ap.add_argument("--lexicon-out", default="grammar/e2e.lexicon")
    ap.add_argument("--rules-out", default="grammar/e2e.rules")
    args = ap.parse_args()

    names = set()
    values: dict[str, set[str]] = {s: set() for s in CONTENT_SLOTS}
    no_name = 0

    for row in read_items(Path(args.lexicon_items)):
        slots = row["expected_slots"]
        if "name" in slots:
            names.add(clean_value(slots["name"]))
        else:
            no_name += 1
        for slot in CONTENT_SLOTS:
            if slot in slots:
                values[slot].add(clean_value(slots[slot]))

    lex: list[str] = [
        "/************************************************************",
        "* E2E lexicon generated from the training split.",
        "* Test-only values are not added by this script.",
        "************************************************************/",
        "",
        "FORM form;",
        "",
        "/*** Subject forms ***/",
        '"The restaurant" generic_subject [];',
    ]
    for name in sorted(names):
        lex.append(f"{q(name)} name [name:{q(name)}];")

    lex += [
        "",
        "/*** Clause markers ***/",
        '"is" copula [];',
        '"serves" serve_marker [];',
        '"has" have_marker [];',
        '"and" coord [];',
        "",
        "/*** Slot values ***/",
    ]
    for slot in CONTENT_SLOTS:
        cat = VALUE_CAT_FOR_SLOT[slot]
        if values[slot]:
            lex.append(f"/** {slot} **/")
            for value in sorted(values[slot]):
                lex.append(
                    f"{q(value_surface(slot, value))} {cat} [{slot}:{q(value)}];"
                )
            lex.append("")

    lexicon_out = Path(args.lexicon_out)
    rules_out = Path(args.rules_out)
    lexicon_out.parent.mkdir(parents=True, exist_ok=True)
    rules_out.parent.mkdir(parents=True, exist_ok=True)
    lexicon_out.write_text("\n".join(lex) + "\n", encoding="utf-8")
    write_rules(rules_out)

    print(json.dumps({
        "lexicon_source": str(args.lexicon_items),
        "names": len(names),
        "no_name_items": no_name,
        "slot_values": {slot: len(values[slot]) for slot in CONTENT_SLOTS},
        "rule_combinations": 2 ** len(CONTENT_SLOTS) * 2 - 1,
        "lexicon_out": str(lexicon_out),
        "rules_out": str(rules_out),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
