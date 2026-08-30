# E2E/GEM benchmark

This directory reproduces the E2E/GEM experiment reported in the Elvex paper.
It is a closed-domain realization test: Elvex receives the meaning
representation (MR), generates licensed realizations, and the evaluation checks
whether the explicit input slots are preserved.

## Protocol

The pipeline reproduces the `GEM/e2e_nlg` E2E configuration without relying on
the Hugging Face cache or API. It downloads the public source files used by
that configuration directly and verifies their SHA-256 checksums before use.

- training lexical inventory: `train-fixed.no-ol.csv` from `tuetschek/e2e-cleaning`;
- evaluation data: GEM's public `e2e/test.json`.

- The **test split** is the evaluation set.
- The **training split** is used only to build the closed-domain lexical
  inventory (restaurant names and slot values).
- Grammar rules are generic over E2E slot combinations; they are not learned
  from the test split.
- Each input contains an exact `slotset` signature. A rule must match that
  signature, so a rule realizing only a subset of the MR cannot license an
  output for a richer MR.
- The pipeline preserves every human reference supplied in the GEM `references`
  field. References are retained for inspection but are not used by the slot
  preservation metrics.

For the current GEM test split, the preparation step requires the following
invariants:

- 1,847 input MRs
- 11,428 explicit input slots
- 4,693 human references

A mismatch is treated as an error rather than silently producing a different
benchmark.

## What is measured

`First output` evaluates the first Elvex realization for each input.

`Best in forest` is an oracle-style diagnostic that chooses, after generation,
the realization with the fewest omitted input slots. It is not a runtime
ranker.

`All outputs` additionally verifies whether every realization enumerated for an
input is slot-complete. This diagnostic is useful because exact `slotset`
matching is intended to prevent partial-MR realizations from entering the
forest.

The main metrics are:

- generation coverage: inputs with at least one generated realization;
- slot accuracy: proportion of input slots present in the selected realization;
- SER: slot omission rate;
- output count: mean number of compatible realizations per input.

These are realization diagnostics, not reference-based E2E leaderboard scores.

## Requirements

Python 3 is required; the benchmark uses only the Python standard library, so
no `pip` installation or Hugging Face token is needed. A working `elvex` binary
must be available on `PATH`, or set `ELVEX_BIN`.

## Prepare the full benchmark

```bash
./prepare_full.sh
```

This downloads and checksum-verifies the train and test source files, checks
the test-set invariants, creates one Elvex input per test MR, builds the grammar,
and constructs the lexicon from the train split. It does **not** run Elvex.

To prepare and immediately run the full generation benchmark, use:

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

`lexicon_coverage.json` records any test slot values absent from the training
lexical inventory. No test-only lexical item is silently added to the lexicon.

## Full run

```bash
./run_full.sh
```

Useful overrides:

```bash
ELVEX_BIN=/path/to/elvex ./run_full.sh
ELVEX_MAX_TIME=60 ./run_full.sh
ELVEX_MAX_LENGTH=80 ./run_full.sh
ELVEX_MAX_ITEMS=100000 ./run_full.sh
```

The main result files are:

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

After a full run, validate the dataset invariants, raw Elvex process results,
metric arithmetic, and slot completeness with:

```bash
./check_results.py
```

The checker exits non-zero if any Elvex process failed, if metric totals disagree
with the raw output file, or if any generated realization omits an input slot.

## Smoke test

```bash
./run_smoke.sh
```

The smoke test uses a few test MRs but still builds its lexical inventory from
the training split.

## Git hygiene

`runs/` and `.venv/` are generated locally and ignored by Git. After preparing
or running the benchmark, `git status` should therefore show only intentional
changes to source files or hand-maintained documentation.

Named and unnamed inputs use distinct subject nonterminals: a supplied `name` must be realized by that exact lexical entry, while an input without a `name` uses only the generic subject. This prevents both name omission and unsupported restaurant-name insertion.
