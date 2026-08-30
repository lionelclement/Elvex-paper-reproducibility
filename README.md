# Elvex paper reproducibility repository

This repository contains the tests, benchmarks, experimental scripts,
and results used in the Elvex paper.

The Elvex source code itself is maintained in the main Elvex repository.

## Elvex version

The exact Elvex commit used for these experiments is recorded in:

    ELVEX_COMMIT

## Contents

### Tests

`test/regression/`

Regression tests for the Elvex generator.

`test/paper_support_context/`

Experiments comparing generation with and without contextual support.

### Benchmarks

`benchmark/benchmark-E2E/`

E2E and WebNLG benchmark scripts, grammars, evaluation programs,
and experimental results.

`benchmark/e2e_gem_repro/`

Reproduction pipeline for the GEM E2E dataset.

`benchmark/webnlg/`

WebNLG benchmark pipeline.

Large generated inputs and externally distributed datasets are not
stored in this repository. They are generated or downloaded by the
provided scripts.

## Requirements

A working installation of Elvex is required.

See the README files in each experiment directory for experiment-specific
requirements and commands.

## License

See `LICENSE`.
