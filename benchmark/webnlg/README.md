# WebNLG v2.1 local RDF realization benchmark

This directory reproduces the WebNLG experiment reported in the paper. It
evaluates **local realization of entries containing one to three modified RDF
triples** using explicit Elvex predicate frames and fallback rules.

The scope is narrower than a complete RDF-to-text system: Elvex does not infer
arbitrary RDF semantics, global document ordering, or a complete discourse
plan. Reference scores are oracle-style best-of-forest diagnostics, not
leaderboard-comparable single-output scores.

## Data provenance

The WebNLG source repository and revision are pinned in `user/sources.json`:

```text
https://gitlab.com/shimorina/webnlg-dataset.git
revision 587fa698bec705efbefe72a235a6019c2b9b8b6c
```

The benchmark uses:

- WebNLG `release_v2.1/xml`;
- `modifiedtripleset` / `mtriple` RDF triples;
- direct `<lex>` elements as sentence references;
- the official test split;
- entries containing exactly 1, 2, or 3 modified triples.

Expected test-set input counts are:

```text
1 triple: 388
2 triples: 298
3 triples: 331
```

`./run data-check` verifies the release, split, and size invariants.

## Metrics

For each graph size, the scorer reports:

- input count;
- inputs with at least one generated realization;
- generation coverage;
- mean compatible realizations per generated input;
- best-of-forest exact and normalized exact match with a human reference;
- mean sentence-level best-of-forest BLEU;
- mean sentence-level best-of-forest chrF.

These metrics measure local realization coverage and reference overlap. The
experiment does not report separate correctness scores for repeated entities,
local frame combination, typed relatives, or fallback.

## Expected results

| triples | inputs | generated | coverage | mean outputs | exact | norm. exact | BLEU | chrF |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 388 | 378 | 97.4% | 2.44 | 29.9% | 31.2% | 66.58 | 83.44 |
| 2 | 298 | 286 | 96.0% | 10.37 | 0.0% | 0.0% | 43.60 | 71.56 |
| 3 | 331 | 317 | 95.8% | 41.23 | 0.0% | 0.0% | 38.44 | 67.60 |

Machine-readable summaries are written to:

```text
build/reports/comparison_1_triples.summary.json
build/reports/comparison_2_triples.summary.json
build/reports/comparison_3_triples.summary.json
```

Per-input reports are written to
`build/reports/comparison_<n>_triples.tsv`.

## Requirements

- Python 3.10 or newer;
- Git;
- `elvex` on `PATH` for generation;
- `elvexlexicon` on `PATH` for compacted-lexicon construction.

Python dependencies are listed in `requirements.txt`. The `./run` wrapper
creates and manages a local `.venv`.

## Reproduce the benchmark

From `benchmark/webnlg/`:

```bash
./run setup
./run download
./run extract
./run data-check
./run lexicon
./run compact
./run select
./run inputs 1
./run inputs 2
./run inputs 3
./run validate
./run compare 1 0
./run compare 2 0
./run compare 3 0
```

For `compare`, a limit of `0` means all selected inputs.

Generation limits can be overridden if needed, for example:

```bash
ELVEX_MAX_ITEMS=500000 ./run compare 3 0
```

Other supported commands are listed by:

```bash
./run help
```

## Main pipeline artifacts

Extraction:

```text
data/processed/triples.jsonl
```

Selected official-test sequences:

```text
build/sequences/1.jsonl
build/sequences/2.jsonl
build/sequences/3.jsonl
```

Generated Elvex inputs:

```text
build/inputs/simple_triples/   # 1 triple
build/inputs/2_triples/        # 2 triples
build/inputs/3_triples/        # 3 triples
```

Each input directory has an `.index.tsv` with source metadata, triples, and
human references.

The main hand-maintained realization resources are:

```text
user/main.rules
user/lexicon/base.lexicon
user/lexicon/predicate_overrides.tsv
user/rules/frames.rules
user/rules/simple_triples.rules
```

Generated/open-class compacted-lexicon resources include `user/main.pattern`
and `user/main.morpho`; `./run compact` builds `build/lexicon/main.tbl` and
`build/lexicon/main.fsa` with `elvexlexicon`.

## Inspect individual examples

Run one selected input and display its triples, references, generated outputs,
and scores:

```bash
./run compare-one 1 1
./run compare-one 2 1
./run compare-one 3 1
```

A small diagnostic batch can be run with, for example:

```bash
./run compare 2 20
```

## Output normalization and scoring

The comparison pipeline applies final sentence capitalization and
punctuation-spacing normalization before reference matching. Raw outputs are
retained separately.

`best_normalized_match` normalizes case, whitespace, and spaces before
punctuation. BLEU and chrF are computed with SacreBLEU at sentence level. For
exact match, normalized exact match, BLEU, and chrF, the best score among the
generated realizations is retained for each generated input.

These are reference-overlap diagnostics for the generated forest, not a
runtime output-selection model.
