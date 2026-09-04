# `en-oper1` lexical resource

This directory is the dedicated English lexical resource used by the paper's
support-verb ablation. It is intentionally small and experiment-specific: it
contains the 12 curated `Oper1` predicative-noun relations and the nine support
verbs reported in the paper.

The resource is committed here so that reproducing the lexical-context
experiment does not depend on a separate, evolving English grammar directory.
Its initial contents correspond exactly to the 12-case lexical snapshot that
the reproducibility repository previously derived from `Elvex/test/en-llm` at
the Elvex revision recorded in the repository-level `ELVEX_COMMIT`. After this
split, `en-oper1` is the canonical source resource for the paper experiment.

Files:

- `en-lexical-functions.tsv` — curated `Oper1` noun/support relations;
- `en-predicative-nouns.tsv` — predicative-noun profiles used by the cases;
- `en-support-verb-profiles.tsv` — profiles for the nine support verbs;
- `en.morpho` — the minimal noun and present-3sg morphology needed to render
  the benchmark cases.

`../../extract_cases.py` normalizes this resource into the committed
`../../cases.tsv` snapshot. To verify that the snapshot matches the resource:

```bash
python3 benchmark/lexical-context/extract_cases.py --check
```

The resource defines the lexical relations tested by the experiment. The
experiment evaluates whether Elvex propagates the support-verb constraint
through synthesized context; it does not evaluate automatic acquisition of
these lexical relations.
