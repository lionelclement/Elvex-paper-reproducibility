# Benchmarks used in the paper

The paper reports three evaluation pipelines. They answer different questions
and should be interpreted separately.

## `lexical-context/`

Direct ablation of synthesized support-verb context on 12 curated `Oper1`
predicative-noun relations covering nine support verbs.

- FULL reuses the support constraint synthesized by the noun.
- NO-CONTEXT suppresses that reuse.
- PRE-SPECIFIED supplies the correct support constraint in the input.

Expected result: FULL and PRE-SPECIFIED each license the 12 compatible
realizations only; NO-CONTEXT preserves those 12 and licenses 96 additional
incompatible noun/support combinations.

## `e2e/`

Closed-domain generation coverage and explicit input-slot preservation on the
full E2E/GEM test split. The lexical inventory is built from the training split
only.

Expected result: 1,847/1,847 inputs generated and 11,428/11,428 input slots
preserved.

## `webnlg/`

Local RDF realization on the WebNLG v2.1 official test split, restricted to
entries containing one to three modified RDF triples. Reported quantities are
generation coverage, mean compatible realizations, and oracle-style
best-of-forest reference-overlap scores.

This experiment is not a full WebNLG pipeline, a leaderboard comparison, or a
phenomenon-specific structural-accuracy evaluation.

The README in each benchmark directory documents data provenance, requirements,
reproduction commands, result files, and the expected values reported in the
paper.
