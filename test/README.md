# Elvex regression tests

This directory contains implementation-level regression tests for the Elvex
behaviour used by the paper. The runner automatically discovers every
`test/regression/*.rules` file; the current snapshot contains **41 tests**.

These tests support the implementation mechanisms used in the paper. They are
not, by themselves, a benchmark of linguistic phenomena such as anaphora,
register, or gender.

## Requirements

A working `elvex` executable is required. Tests that build a compacted lexicon
also require `elvexlexicon`.

From the repository root, run:

```bash
test/run-regression.sh /path/to/elvex /path/to/elvexlexicon
```

If the binaries are available through the environment:

```bash
ELVEX_BIN=/path/to/elvex \
ELVEXLEXICON_BIN=/path/to/elvexlexicon \
  test/run-regression.sh
```

The second executable is only needed by cases with `.pattern` / `.morpho`
resources, but supplying both paths makes the full suite reproducible.

## Test-file convention

For a case named `NN_name`, the runner expects:

```text
NN_name.rules
NN_name.lexicon
NN_name.expected
NN_name.input       # usual input mode
```

A case may use `NN_name.stdin` instead of `.input`; in that case Elvex is run in
`--server-stdio` mode. Optional resources include:

```text
NN_name.stderr
NN_name.macros
NN_name.pattern
NN_name.morpho
```

When `.pattern` or `.morpho` is present, the runner builds a temporary compacted
lexicon with `elvexlexicon` and passes it to Elvex.

## Comparison semantics

Generated stdout is compared **without depending on generation order**. The
normalization performed by `run-regression.sh` is exactly:

1. normalize CRLF line endings;
2. remove non-printing control characters handled by the runner;
3. canonicalize whitespace-only lines to true empty lines;
4. **keep empty lines**;
5. sort complete output lines as atomic strings before comparison.

Words inside a line are never reordered. Duplicate lines are also retained, so
this is an order-insensitive comparison of output lines rather than a
set-deduplication step.

Elvex instrumentation lines beginning with `ELVEX_METRICS_HEADER` or
`ELVEX_METRICS` are filtered from stderr before stderr comparison. Other stderr
is either compared with `NN_name.stderr`, when present, or reported as a
warning.

## Current coverage

The 41-case snapshot includes tests for:

- required, optional, and alternative daughters;
- `#i`, `#i.j`, negated-presence, and cross-dependency conditions;
- fixed, boundary, partial, unordered, optional, and synthesized-key ordering;
- guards, subsumption, unification, nested feature access, and feature tests;
- arithmetic, boolean/logical expressions, assignments, and deferred
  evaluation;
- synthesized and inherited attribute assignment;
- compacted-lexicon construction and use;
- stdout/stderr-producing built-ins and server-stdio input.

The tests most directly related to mechanisms discussed in the paper include:

- `13_order_by_field` — ordering by a synthesized field;
- `29_deferred_synthesized_child` — a child result becoming available before a
  deferred dependent statement can be evaluated;
- `35_assign_synthesized_attribute` — synthesized-attribute assignment;
- `40_deferred_bool_expr` — deferred evaluation of an expression with missing
  operands.

The exact suite is defined by the filenames in `test/regression/`; adding a new
`.rules` case automatically includes it in the next run.
