# Elvex paper reproducibility repository

This repository contains the resources, scripts, regression tests, and result
snapshots used to reproduce the experiments in *A Constraint-Based Formalism
for Controlled Text Generation*.

The Elvex implementation is maintained separately. The exact Elvex revision
used for the experiments is recorded in `ELVEX_COMMIT`.

## Experiments reported in the paper

### Lexical-context ablation

`benchmark/lexical-context/`

A controlled FULL / NO-CONTEXT / PRE-SPECIFIED comparison on 12 curated
`Oper1` predicative-noun relations covering nine support verbs. The experiment
tests whether a support-verb constraint produced during nominal realization can
constrain a later verbal realization without being supplied in the initial
semantic input.

Expected structural result:

```text
condition       licensed  compatible  incompatible
FULL                  12          12             0
PRE-SPECIFIED         12          12             0
NO-CONTEXT           108          12            96
```

See `benchmark/lexical-context/README.md`.

### E2E/GEM

`benchmark/e2e/`

Closed-domain generation coverage and input-slot preservation on the full
E2E/GEM test split. The lexical inventory is constructed from the training
split only.

Expected result: all 1,847 test inputs generate and all 11,428 explicit input
slots are preserved.

See `benchmark/e2e/README.md`.

### WebNLG

`benchmark/webnlg/`

Local RDF realization on the WebNLG v2.1 official test split for entries with
one to three modified RDF triples. The paper reports generation coverage and
oracle-style best-of-forest reference overlap. This is not a full RDF-to-text
pipeline or a leaderboard comparison.

See `benchmark/webnlg/README.md`.

## Regression and supplementary tests

`test/regression/` contains implementation-level regression cases for grammar
control, feature structures, ordering, deferred evaluation, synthesized
attributes, compacted lexicons, and related Elvex behaviour. These tests check
mechanisms used by the paper; they are not a linguistic benchmark.

`test/paper_support_context/` contains a supplementary synthetic search-space
stress test. It is not one of the three evaluation experiments reported in the
current paper.

See `test/README.md` and `test/paper_support_context/README.md`.

## Requirements

A working Elvex installation is required for fresh generator runs. Commands
that invoke Elvex expect `elvex` and, where compacted lexicons are built,
`elvexlexicon` to be available on `PATH` or supplied through the options or
environment variables documented in each experiment directory.

Check the pinned revision with:

```bash
cat ELVEX_COMMIT
```

If the Elvex source is checked out as a sibling directory, select that revision
with:

```bash
git -C ../Elvex checkout "$(cat ELVEX_COMMIT)"
```

Downloaded corpora and generated benchmark products are normally ignored by
Git. Small reference snapshots needed to verify the numerical claims are
committed in the relevant experiment directories.

## Repository validation

From the repository root:

```bash
python3 validate_repo.py
```

Require generated E2E/WebNLG artifacts to be present:

```bash
python3 validate_repo.py --require-generated
```

Require the Elvex executables and rerun Elvex-dependent checks:

```bash
python3 validate_repo.py --require-generated --require-elvex
```

Each experiment README gives the commands for regenerating its inputs, outputs,
and reported metrics.

## License

See `LICENSE`.
