# E2E/GEM closed-domain realization benchmark

This directory reproduces the E2E/GEM experiment reported in the paper. The
experiment measures **generation coverage and preservation of explicit input
slots** in the controlled restaurant domain.

Reference similarity is not used as the primary metric.

## Data protocol

The pipeline reproduces the `GEM/e2e_nlg` E2E configuration from public source
files and verifies their SHA-256 checksums.

- lexical inventory source: `train-fixed.no-ol.csv` from `tuetschek/e2e-cleaning`;
- evaluation source: GEM's public `e2e/test.json`;
- evaluation split: official test split;
- lexical inventory: built from the training split only;
- human references: retained for inspection, but not used to compute slot
  preservation.

The preparation step verifies:

```text
1,847 input meaning representations
11,428 explicit input slots
4,693 human references
```

`runs/full/lexicon_coverage.json` records whether any test slot value is absent
from the training lexical inventory. For the reported experiment, all test
values are observed in training.

## Metrics

- **coverage**: proportion of input MRs with at least one generated realization;
- **slot accuracy**: proportion of explicit input slots realized;
- **SER**: input-slot omission rate;
- **mean outputs**: mean number of compatible realizations per input.

Each generated input contains an exact `slotset` signature, so a rule that
realizes only a subset of an MR cannot license a realization for a richer MR.

## Expected result

```text
inputs   coverage   slots   slot_accuracy   SER   mean_outputs
1847     100.0%     11428   100.0%          0.0%  1.00
```

Thus all 1,847 test MRs generate and all 11,428 explicit input slots are
preserved.

## Requirements

Python 3 is required. The benchmark uses only Python standard-library modules.
A working `elvex` executable must be available on `PATH`, or supplied through
`ELVEX_BIN` for generation.

## Reproduce the benchmark

From `benchmark/e2e/`, prepare the verified data and generated resources:

```bash
./prepare_full.sh
```

Run generation:

```bash
./run_full.sh
```

Or prepare and run generation in one command:

```bash
./prepare_full.sh --run-generation
```

Useful overrides are:

```bash
ELVEX_BIN=/path/to/elvex ./run_full.sh
ELVEX_MAX_TIME=60 ./run_full.sh
ELVEX_MAX_LENGTH=80 ./run_full.sh
ELVEX_MAX_ITEMS=100000 ./run_full.sh
```

## Validate the result

After generation:

```bash
./check_results.py
```

The checker verifies the dataset invariants, process success, agreement between
raw outputs and metric files, and preservation of every input slot.

For a short end-to-end check:

```bash
./run_smoke.sh
```

The smoke test evaluates only a small number of test MRs but still constructs
its lexical inventory from the training split.

## Main generated artifacts

```text
runs/full/dataset_summary.json
runs/full/lexicon_coverage.json
runs/full/manifest_test.jsonl
runs/full/grammar/e2e.rules
runs/full/grammar/e2e.lexicon
runs/full/outputs_test_all.jsonl
runs/full/metrics_first_output.json
runs/full/metrics_best_in_forest.json
runs/full/metrics_all_outputs.json
```

`runs/` is generated locally and ignored by Git.
