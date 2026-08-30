# Elvex paper reproducibility repository

This repository contains the tests and benchmarks used in the Elvex paper.
The Elvex source code itself is maintained in the main Elvex repository.

## Elvex version

The exact Elvex commit used for the experiments is recorded in:

    ELVEX_COMMIT

## Contents

### Tests

`test/regression/`

Regression tests for the Elvex generator.

`test/paper_support_context/`

Controlled experiment comparing generation with and without reuse of
synthesized support-verb information.

### Benchmarks

`benchmark/e2e/`

E2E/GEM closed-domain realization benchmark. The pipeline downloads and
checksum-verifies the public E2E/GEM source files directly, builds the lexical
inventory from the training split, evaluates the official test split, and
checks generation coverage and slot preservation.

`benchmark/webnlg/`

WebNLG v2.1 local RDF realization benchmark on the official test split,
restricted to one-to-three modified RDF triples.

See `benchmark/README.md` and the README in each benchmark directory for the
exact protocol and commands.

Large downloaded datasets, generated inputs, virtual environments, logs, and
other build artifacts are intentionally not stored in Git; the benchmark
scripts recreate them locally.

## Requirements

A working installation of Elvex is required.

See the README files in each experiment directory for exact commands. The E2E
benchmark uses only Python 3 standard-library modules; WebNLG documents its own
requirements.

## Repository validation

Run the source-level tests, Git-hygiene checks, stored controlled-ablation
consistency checks, and any locally available benchmark-result checks with:

```bash
python3 validate_repo.py
```

For a machine on which both complete benchmark runs and Elvex are available:

```bash
python3 validate_repo.py --require-generated --require-elvex
```

Add `--require-pinned-head` (and, if necessary, `--elvex-repo PATH`) when the
Elvex checkout itself must be at exactly the commit recorded in `ELVEX_COMMIT`.

## License

See `LICENSE`.
