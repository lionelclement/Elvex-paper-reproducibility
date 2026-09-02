# WebNLG v2.1 local RDF realization benchmark

This directory reproduces the WebNLG experiment reported in the camera-ready
Elvex paper. It evaluates **local realization of one-to-three modified RDF
triples** with explicit Elvex frames and fallback rules.

The scope is deliberately narrower than a full WebNLG RDF-to-text system:
Elvex does not infer arbitrary RDF semantics, global document ordering, or a
complete discourse plan. The reported reference scores are oracle-style
best-of-forest diagnostics, not leaderboard-comparable single-output scores.

## Data provenance and benchmark scope

The source repository is pinned in `user/sources.json`:

```text
https://gitlab.com/shimorina/webnlg-dataset.git
revision 587fa698bec705efbefe72a235a6019c2b9b8b6c
```

The benchmark uses:

- WebNLG `release_v2.1/xml`;
- `modifiedtripleset` / `mtriple` RDF triples;
- direct `<lex>` elements as sentence references;
- the official **test** split;
- native entries containing exactly 1, 2, or 3 modified triples;
- no splitting of larger entries into artificial one-triple benchmark examples;
- no triple deduplication or near-duplicate merging before Elvex input
  generation.

The expected official test-set counts are:

```text
1 triple: 388 inputs
2 triples: 298 inputs
3 triples: 331 inputs
```

`./run data-check` verifies the release, split, and size invariants. The expected
number of extracted entries across train/dev/test is 16,095.

## What the paper measures

For each graph size, the batch scorer reports:

- input count;
- inputs with at least one generated realization;
- generation coverage;
- mean compatible realizations per generated input;
- best-of-forest exact match with any human reference;
- best-of-forest normalized exact match;
- mean sentence-level best-of-forest BLEU;
- mean sentence-level best-of-forest chrF.

These metrics measure **local realization coverage and reference overlap**.
Although the grammar contains resources for local frame combination, repeated
entities, typed relatives, and fallback, this table is **not** a
phenomenon-specific structural-accuracy evaluation.

## Camera-ready results

The expected summaries for the pinned resources are:

| triples | inputs | generated | coverage | mean outputs | exact | norm. exact | BLEU | chrF |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 388 | 378 | 97.4% | 2.44 | 29.9% | 31.2% | 66.58 | 83.44 |
| 2 | 298 | 286 | 96.0% | 10.37 | 0.0% | 0.0% | 43.60 | 71.56 |
| 3 | 331 | 317 | 95.8% | 41.23 | 0.0% | 0.0% | 38.44 | 67.60 |

The machine-readable results are written to:

```text
build/reports/comparison_1_triples.summary.json
build/reports/comparison_2_triples.summary.json
build/reports/comparison_3_triples.summary.json
```

The corresponding per-input reports are
`build/reports/comparison_<n>_triples.tsv`.

## Requirements

The wrapper requires:

- Python 3.10 or newer;
- Git for downloading the pinned dataset repository;
- `elvex` on `PATH` for generation;
- `elvexlexicon` on `PATH` for compacted-lexicon construction.

Python dependencies are listed in `requirements.txt` (`sacrebleu` for the
reference-overlap metrics). The `./run` wrapper creates and manages a local
`.venv`.

On macOS with Homebrew, for example:

```bash
brew install python git
cd benchmark/webnlg
./run setup
```

## Reproduce the paper benchmark

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

For `compare`, a limit of `0` means **all selected inputs**. The shorter
`./run all` command is a project bootstrap and prepares the one-triple sample;
the explicit commands above are the reproducibility protocol for all three
paper rows.

Generation limits can be overridden when necessary:

```bash
ELVEX_MAX_ITEMS=200000
ELVEX_MAX_TIME=60
ELVEX_PROCESS_TIMEOUT=70
```

For example:

```bash
ELVEX_MAX_ITEMS=500000 ./run compare 3 0
```

## Pipeline artifacts

### Extraction and selection

`./run extract` writes:

```text
data/processed/triples.jsonl
```

`./run select` writes size-specific official-test sequences:

```text
build/sequences/1.jsonl
build/sequences/2.jsonl
build/sequences/3.jsonl
```

### Elvex inputs

`./run inputs <n>` creates one Elvex input per WebNLG entry:

```text
build/inputs/simple_triples/   # n = 1
build/inputs/2_triples/        # n = 2
build/inputs/3_triples/        # n = 3
```

Each directory has an `.index.tsv` carrying source metadata, triples, and human
references. Concatenated `.input` diagnostics may also be produced for
inspection; they must not be passed to Elvex as a single generation request.

### Lexical resources

The generated/open-class compacted-lexicon resources are:

```text
user/main.pattern
user/main.morpho
```

Hand-maintained additions live in:

```text
user/override.pattern
user/override.morpho
user/lexicon/base.lexicon
user/lexicon/predicate_overrides.tsv
user/rules/frames.rules
user/rules/simple_triples.rules
```

`./run compact` builds:

```text
build/lexicon/main.tbl
build/lexicon/main.fsa
```

using `elvexlexicon` with `user/main.macros`, `user/main.pattern`, and
`user/main.morpho`.

## Inspect individual examples

Run one selected input and show its triples, references, generated outputs, and
scores:

```bash
./run compare-one 1 1
./run compare-one 2 1
./run compare-one 3 1
```

Run a small diagnostic batch:

```bash
./run compare 1 20
./run compare 2 20
./run compare 3 20
```

Raw and finalized outputs are retained under `build/outputs/compare/`, with
Elvex logs under `build/logs/elvex/`.

## Output normalization and reference scores

Elvex resources keep ordinary function words lowercase and preserve proper-name
capitalization. The comparison pipeline applies final sentence capitalization
and punctuation-spacing normalization before reference matching. Raw outputs
are retained separately from finalized outputs.

`best_normalized_match` performs only light normalization of case, whitespace,
and spaces before punctuation. It is a development/reference-overlap
diagnostic, not an official WebNLG metric.

BLEU and chrF are computed with SacreBLEU at sentence level and the best score
among the generated forest realizations is retained for each generated input.

## Important interpretation

The grammar includes explicit predicate frames, local combination rules,
repeated-entity handling, relative constructions, numeric realization, and
controlled fallback. However, the camera-ready experiment reports aggregate
coverage and reference overlap only. It should therefore be interpreted as a
**local RDF realization test**, not as evidence that each listed structural
phenomenon has been independently measured for correctness.
