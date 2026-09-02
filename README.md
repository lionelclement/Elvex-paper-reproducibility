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

`benchmark/lexical-context/`

Direct FULL/NO-CONTEXT/PRE-SPECIFIED ablation on 12 independently curated
predicative-noun constructions and nine support verbs. Unlike the repeated
binary support-verb stress test, this benchmark evaluates lexical compatibility
on a snapshot extracted from the English Elvex resources. It also provides a
30-run timing protocol and balanced heterogeneous panels combining distinct
constructions for `N=1..4`.

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

A working installation of Elvex is required. The `elvex` and `elvexlexicon`
commands should be available on `PATH`; alternatively, set `ELVEX_BIN` and
`ELVEXLEXICON_BIN` to their executable paths. Validation treats Elvex as an
installed dependency and does not inspect or modify an Elvex source checkout.

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

When `elvex` is available, the validator also reruns the complete 12-case
FULL/NO-CONTEXT/PRE-SPECIFIED lexical-context ablation in a temporary directory
and checks its fresh structural results. The committed result snapshot is not
modified.

Run the repeated timing protocol and heterogeneous composition test in addition
to the default checks with:

```bash
python3 validate_repo.py --require-elvex --run-extended-context
```

`ELVEX_COMMIT` records the Elvex source version used for the published
experiments. It is provenance metadata; the validator does not require access
to an Elvex source repository.

## License

See `LICENSE`.
