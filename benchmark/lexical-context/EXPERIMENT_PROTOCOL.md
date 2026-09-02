# Context-reuse evaluation protocol

## Purpose

The repeated `2^N` versus `4^N` support-verb experiment is a controlled search
stress test. It is not, by itself, strong empirical evidence that synthesized
context helps on varied linguistic decisions. The paper should therefore use
two complementary evaluations:

1. a linguistically grounded lexical ablation as the primary direct test;
2. the repeated binary construction as a secondary scalability stress test.

The committed lexical snapshot already supplies the first layer: 12 distinct
predicative nouns, nine support verbs, and seven semantic classes extracted from
the independently maintained `Elvex/test/en-llm` resources.

## Primary experiment: lexical compatibility

### Conditions

- **FULL**: the predicative noun is selected from an underspecified semantic
  input and its synthesized support structure constrains the verb.
- **NO-CONTEXT**: noun and support verb are selected independently. This must
  retain the compatible realization; the intervention removes only the
  information channel and must not remove lexical resources.
- **PRE-SPECIFIED**: the compatible support structure is supplied in the input.
  This is a sufficiency control and an upper bound for FULL.

### Confirmatory hypotheses

- H1: FULL and PRE-SPECIFIED produce the same valid realization for every case.
- H2: FULL produces no incompatible noun/support pair.
- H3: NO-CONTEXT retains every compatible pair but licenses additional
  incompatible pairs.
- H4: in heterogeneous panels, FULL retains the compatible sequence while
  NO-CONTEXT licenses the complete `9^N` cross-frame product.
- H5: FULL uses fewer chart items and forest edges than NO-CONTEXT when the
  installed Elvex executable emits structural metrics.

H1-H4 concern linguistic validity and are deterministic for a fixed resource
snapshot. H5 concerns computational cost. Timings should be reported using
repeated runs rather than a single measurement.

### Primary measures

- case-level exact-set agreement between FULL and PRE-SPECIFIED;
- compatible realizations / all licensed realizations;
- spurious realizations per case;
- generation failures;
- whether the compatible realization survives the ablation.

Raw output counts are secondary. Validity must be macro-averaged by case so a
case with many alternatives cannot dominate the result.

### Computational measures

For each case and condition, record at least 20 runs after two warm-up runs:

- wall-clock time: median, p90, p95, and maximum;
- peak resident memory;
- chart items inserted;
- packed nodes and forest edges;
- saturation passes and maximum passes per saturation call;
- enumerated outputs.

Structural counts are deterministic. Timings are machine-dependent and must be
reported with the Elvex commit, compiler/build mode, CPU, memory, OS, and run
protocol.

The supplied confirmatory command uses 30 measured repetitions and cycles
through all six condition orders:

```bash
python3 benchmark/lexical-context/run_repeated.py --warmups 2 --repeats 30
```

### Acceptance criteria

The result is suitable for a paper claim only if:

- all 12 FULL cases and all 12 PRE-SPECIFIED cases generate exactly one
  compatible output and no incompatible output;
- all 12 NO-CONTEXT cases retain the compatible output;
- the committed `reference-results.tsv` snapshot passes `check_results.py`;
- the committed timing snapshots pass `check_timing_results.py`, which
  recomputes the summary statistics from all 30 measured repetitions;
- a fresh run at the pinned Elvex commit reproduces the structural counts;
- the source snapshot is reproduced by `extract_cases.py --check`.

For the committed snapshot, the reported structural result is:

| Condition | Cases | Distinct support verbs | Compatible | Licensed | Spurious | Compatible % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| FULL | 12 | 9 | 12 | 12 | 0 | 100.0 |
| PRE-SPECIFIED | 12 | 9 | 12 | 12 | 0 | 100.0 |
| NO-CONTEXT | 12 | 9 | 12 | 108 | 96 | 11.1 |

The committed timing snapshot used for the paper reports:

| Condition | Runs | Median (ms) | p95 (ms) |
| --- | ---: | ---: | ---: |
| FULL | 30 | 18.480 | 19.920 |
| PRE-SPECIFIED | 30 | 18.931 | 19.979 |
| NO-CONTEXT | 30 | 26.298 | 27.824 |

These machine-dependent values are archived together with all 90 raw
condition-level measurements and the machine/Elvex provenance metadata.

## Secondary experiment: search-space stress

Keep `test/paper_support_context` as a deliberately synthetic experiment. Its
role is to isolate how repeated independent dependencies affect chart size,
forest size, memory, and linearization time. It should not be presented as the
main evidence for linguistic adequacy.

The additional heterogeneous stress test composes distinct constructions
rather than repeating that binary ambiguity. It uses nine cyclic panels for
each `N=1..4`; the panels are balanced over nine distinct support verbs and
contain no repeated support within a panel. FULL must produce one compatible
sequence per panel. NO-CONTEXT must retain that sequence and additionally
license the remaining `9^N - 1` cross-frame combinations.

```bash
python3 benchmark/lexical-context/run_heterogeneous.py --max-n 4
python3 benchmark/lexical-context/check_heterogeneous_results.py \
  --require-complete
```

## Follow-up multi-phenomenon suite

Support-verb selection still tests only one type of contextual dependency. A
stronger follow-up suite should contain at least three additional phenomena,
with independently curated lexical items and the same three conditions.

| Phenomenon | Synthesized decision | Later constraint | Main error without context |
| --- | --- | --- | --- |
| French gender | `voiture` vs `véhicule` | pronoun/adjective agreement | agreement mismatch |
| Register | formal vs informal first mention | anaphoric expression | register clash |
| Lexical frame | nominal lexicalization | support verb and preposition | collocation/frame mismatch |
| Lightness/order | realized NP structure | NP/PP relative order | illicit linearization |

Each phenomenon should include four intervention types:

1. **necessity**: remove synthesized-context reuse;
2. **sufficiency**: pre-specify the relevant feature;
3. **counterfactual mediation**: change only the synthesized feature and verify
   that the dependent realization changes accordingly;
4. **negative control**: alter an irrelevant contextual feature and verify that
   the output set does not change.

This intervention design provides stronger evidence than a larger Cartesian
product: it tests that context is necessary, sufficient, and causally linked to
the downstream decision, while also checking that irrelevant context does not
over-prune the grammar.

## Recommended paper structure

The evaluation section should present experiments in this order:

1. **Lexical-context ablation**: primary direct evidence for context reuse.
2. **Synthetic search stress**: controlled scaling and resource measurements.
3. **E2E/GEM**: closed-domain coverage and slot preservation.
4. **WebNLG**: local RDF realization coverage.

Until the multi-phenomenon suite is run, the conclusion should claim direct
empirical support for phraseological context reuse, not for every motivating
phenomenon (gender, register, anaphora, and ordering). Those remain supported by
formal examples and regression tests rather than by the primary benchmark.
