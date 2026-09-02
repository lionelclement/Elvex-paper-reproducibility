# Elvex paper reproducibility repository

This repository contains the regression tests, controlled ablations, benchmark
pipelines, and machine-readable result snapshots used for the camera-ready Elvex
paper, *A Constraint-Based Formalism for Controlled Text Generation*.

The Elvex implementation itself is maintained separately. The exact source
revision used for the reported experiments is recorded in `ELVEX_COMMIT`.

## Paper-to-repository map

### Regression tests

`test/regression/`

The current suite contains 41 automatically discovered regression cases for the
Elvex generator. They cover grammar control, ordering, feature-structure
operations, deferred evaluation, synthesized attributes, compacted lexicons,
and related implementation behaviour. These are mechanism-level regression
tests, not a phenomenon-specific linguistic benchmark.

See `test/README.md` for the exact runner semantics and commands.

### Synthetic search-space stress test

`test/paper_support_context/`

Repeated binary `pay attention` / `take notice` dependencies compare FULL
context reuse against NO-CONTEXT. The paper reports the `N=1..7` trace and the
`N=7` scaling snapshot. This experiment isolates search-space growth; it is
separate from the direct lexical adequacy ablation below.

### Lexical-context ablation

`benchmark/lexical-context/`

Direct FULL / NO-CONTEXT / PRE-SPECIFIED ablation on 12 curated `Oper1`
predicative-noun constructions extracted from the English Elvex resources,
covering nine distinct support verbs. The directory also contains the 30-run
timing protocol, immutable reference snapshots, and a heterogeneous
nine-support stress test.

### E2E/GEM

`benchmark/e2e/`

Closed-domain realization and input-preservation evaluation on the full
E2E/GEM test split. The lexical inventory is derived from the training split;
the camera-ready result is 1,847/1,847 generated inputs and all 11,428 input
slots preserved.

### WebNLG

`benchmark/webnlg/`

WebNLG v2.1 local RDF realization on the official test split, restricted to
entries containing one to three modified RDF triples. The reported quantities
are generation coverage, mean compatible realizations, and oracle-style
best-of-forest reference overlap. They are not phenomenon-specific structural
accuracy metrics and are not presented as a WebNLG leaderboard result.

See `benchmark/README.md` and the README in each benchmark directory for the
exact protocol and commands.

## Elvex version and requirements

A working installation of Elvex is required for fresh generator runs. The
commands `elvex` and `elvexlexicon` should be available on `PATH` where a
benchmark requires them; some scripts also accept explicit executable paths or
environment variables as documented locally.

For exact provenance, inspect the pinned revision with:

```bash
cat ELVEX_COMMIT
```

If the Elvex source is checked out as a sibling directory, the corresponding
revision can be selected with:

```bash
git -C ../Elvex checkout "$(cat ELVEX_COMMIT)"
```

The repository validator treats Elvex as an installed dependency and does not
modify an Elvex source checkout.

Downloaded corpora, generated inputs, virtual environments, logs, and other
large build artifacts are normally excluded from Git. Small immutable snapshots
needed to verify the paper's numerical claims are committed where appropriate.

## Repository validation

From the repository root, run source-level checks, Git-hygiene checks, stored
controlled-ablation consistency checks, and checks for generated benchmark
results that are already present:

```bash
python3 validate_repo.py
```

Require complete generated benchmark artifacts as well:

```bash
python3 validate_repo.py --require-generated
```

On a machine with the pinned Elvex executables available, require and rerun the
Elvex-dependent checks:

```bash
python3 validate_repo.py --require-generated --require-elvex
```

To additionally run the repeated lexical timing protocol and heterogeneous
composition test:

```bash
python3 validate_repo.py --require-elvex --run-extended-context
```

The detailed benchmark README files document the commands needed to regenerate
their result artifacts from source data.

## License

See `LICENSE`.
