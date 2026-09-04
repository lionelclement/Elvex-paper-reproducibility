# `en-oper1` lexical resource

This directory contains the dedicated English lexical resource used by the
paper's support-verb ablation. It defines the 12 curated `Oper1`
predicative-noun relations and the nine support verbs evaluated by
`benchmark/lexical-context/`.

## Files

- `en-lexical-functions.tsv` — curated `Oper1` noun/support relations;
- `en-predicative-nouns.tsv` — predicative-noun profiles used by the cases;
- `en-support-verb-profiles.tsv` — profiles for the nine support verbs;
- `en.morpho` — minimal noun and present-3sg morphology needed by the benchmark.

`benchmark/lexical-context/extract_cases.py` normalizes this resource into the
committed `benchmark/lexical-context/cases.tsv` snapshot.

From the repository root, verify that the snapshot matches the resource:

```bash
python3 benchmark/lexical-context/extract_cases.py --check
```

The resource supplies the lexical relations used by the controlled experiment.
The experiment tests propagation of the encoded support-verb constraint; it
does not test automatic acquisition of those lexical relations.
