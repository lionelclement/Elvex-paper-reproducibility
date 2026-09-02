# E2E/GEM closed-domain realization benchmark

This directory reproduces the E2E/GEM experiment reported in the camera-ready
Elvex paper. The experiment measures **generation coverage and preservation of
explicit input slots** in a controlled restaurant domain.

It is not an E2E leaderboard experiment and does not use reference similarity
as its primary metric.

## Data protocol

The pipeline reproduces the `GEM/e2e_nlg` E2E configuration without relying on
a Hugging Face cache or API. It downloads the public source files directly and
verifies their SHA-256 checksums.

- lexical inventory source: `train-fixed.no-ol.csv` from `tuetschek/e2e-cleaning`;
- evaluation source: GEM's public `e2e/test.json`;
- evaluation split: official test split;
- lexical inventory: built from the training split only;
- references: retained for inspection, but not used to compute the paper's slot
  preservation result.

The preparation step checks the following invariants:

```text
1,847 input meaning representations
11,428 explicit input slots
4,693 human references
```

A mismatch is treated as an error rather than silently changing the benchmark.
`lexicon_coverage.json` also records any test slot value that is absent from the
training lexical inventory; no test-only lexical item is silently inserted.

## What is measured

The main metrics are:

- **coverage**: proportion of input MRs with at least one generated realization;
- **slot accuracy**: proportion of explicit input slots realized;
- **SER**: input-slot omission rate;
- **output count**: mean number of compatible realizations per input.

Each generated input contains an exact `slotset` signature, so a rule realizing
only a subset of an MR cannot license a realization for a richer MR.

The evaluation code still computes three diagnostics for consistency checking:
`first_output`, `best_in_forest`, and `all_outputs`. In the camera-ready grammar
they coincide, because every test input has exactly one compatible realization
and that realization preserves all slots. The camera-ready paper therefore
reports the aggregate result rather than the older first-vs-oracle contrast.

## Camera-ready result

The expected full-test result for the pinned resources is:

```text
inputs   coverage   slots   slot_accuracy   SER   mean_outputs
1847     100.0%     11428   100.0%          0.0%  1.00
```

Equivalently: all 1,847 test MRs generate, and all 11,428 explicit input slots
are preserved.

## Requirements

Python 3 is required. This benchmark uses only Python standard-library modules,
so no `pip` installation or Hugging Face token is needed.

A working `elvex` executable must be available on `PATH`, or supplied through
`ELVEX_BIN` for the generation step.

## Prepare the benchmark

From `benchmark/e2e/`:

```bash
./prepare_full.sh
```

This downloads and verifies the data, checks the dataset invariants, creates one
Elvex input per test MR, builds the grammar, and constructs the lexical
inventory from the training split. It does **not** run Elvex unless requested.

To prepare and immediately run generation:

```bash
./prepare_full.sh --run-generation
```

Arguments passed to `prepare_full.sh` are forwarded to `rerun_e2e_gem.py`.

Important generated diagnostics include:

```text
runs/full/dataset_summary.json
runs/full/lexicon_coverage.json
runs/full/manifest_test.jsonl
runs/full/grammar/e2e.rules
runs/full/grammar/e2e.lexicon
```

## Run generation

After preparation:

```bash
./run_full.sh
```

Useful overrides include:

```bash
ELVEX_BIN=/path/to/elvex ./run_full.sh
ELVEX_MAX_TIME=60 ./run_full.sh
ELVEX_MAX_LENGTH=80 ./run_full.sh
ELVEX_MAX_ITEMS=100000 ./run_full.sh
```

The main result artifacts are:

```text
runs/full/outputs_test_all.jsonl
runs/full/metrics_first_output.json
runs/full/metrics_best_in_forest.json
runs/full/metrics_all_outputs.json
runs/full/details_first_output.jsonl
runs/full/details_best_in_forest.jsonl
runs/full/details_all_outputs.jsonl
runs/full/table_e2e_gem_results.tex
```

## Validate generated results

Run:

```bash
./check_results.py
```

The checker exits non-zero if dataset invariants fail, an Elvex process failed,
metric totals disagree with the raw output file, or any generated realization
omits an input slot.

## Smoke test

```bash
./run_smoke.sh
```

The smoke test evaluates only a small number of test MRs, but still constructs
its lexical inventory from the training split.

## Git hygiene

`runs/` and `.venv/` are generated locally and ignored by Git. After preparing
or running the benchmark, `git status` should therefore show only intentional
changes to source files or hand-maintained documentation.
