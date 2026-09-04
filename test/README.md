# Elvex regression tests

This directory contains implementation-level regression tests for Elvex
behaviour used by the paper. `test/run-regression.sh` automatically discovers
all `test/regression/*.rules` cases; the current suite contains 41 cases.

These tests verify generator mechanisms. They are not a linguistic benchmark of
anaphora, register, gender, or other phenomena discussed in the paper.

## Requirements and command

A working `elvex` executable is required. Cases that build a compacted lexicon
also require `elvexlexicon`.

From the repository root:

```bash
test/run-regression.sh /path/to/elvex /path/to/elvexlexicon
```

or:

```bash
ELVEX_BIN=/path/to/elvex \
ELVEXLEXICON_BIN=/path/to/elvexlexicon \
  test/run-regression.sh
```

## Test-file convention

For a case named `NN_name`, the usual files are:

```text
NN_name.rules
NN_name.lexicon
NN_name.expected
NN_name.input
```

A case may use `NN_name.stdin` instead of `.input`; Elvex is then run in
`--server-stdio` mode. Optional files include:

```text
NN_name.stderr
NN_name.macros
NN_name.pattern
NN_name.morpho
```

When `.pattern` or `.morpho` is present, the runner builds a temporary compacted
lexicon with `elvexlexicon`.

## Comparison semantics

Generated stdout is compared without depending on the order in which complete
output lines were produced. The runner:

1. normalizes CRLF line endings;
2. removes the non-printing control characters handled by the runner;
3. canonicalizes whitespace-only lines to empty lines;
4. keeps empty lines;
5. sorts complete output lines before comparison.

Words inside a line are never reordered and duplicate lines are retained.

Instrumentation lines beginning with `ELVEX_METRICS_HEADER` or `ELVEX_METRICS`
are filtered from stderr before stderr comparison. Other stderr is compared
with `NN_name.stderr` when that file is present, or otherwise reported as a
warning.

## Coverage

The suite includes cases for:

- required, optional, and alternative daughters;
- cross-dependency and presence conditions;
- fixed, boundary, partial, unordered, optional, and synthesized-field ordering;
- guards, subsumption, unification, nested feature access, and feature tests;
- arithmetic, boolean/logical expressions, assignments, and deferred
  evaluation;
- inherited and synthesized attribute assignment;
- compacted-lexicon construction;
- stdout/stderr built-ins and server-stdio input.

Cases most directly related to mechanisms discussed in the paper include:

- `13_order_by_field` — ordering by a synthesized field;
- `29_deferred_synthesized_child` — deferred use of a synthesized child result;
- `35_assign_synthesized_attribute` — synthesized-attribute assignment;
- `40_deferred_bool_expr` — deferred evaluation with unavailable operands.

The suite is defined by the files in `test/regression/`; adding a `.rules` case
makes it part of the next run automatically.
