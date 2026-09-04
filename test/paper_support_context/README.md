# Supplementary synthetic support-context stress test

This directory contains a synthetic search-space diagnostic for synthesized
support-verb context. It is **not one of the evaluation experiments reported in
the current paper**; it is retained as a compact mechanism/stress test for the
same context-reuse implementation.

## Construction

For one clause, the object can be lexicalized as:

- `attention`, synthesizing `support:PAY`;
- `notice`, synthesizing `support:TAKE`.

The available support verbs are `pays` (`HEAD:PAY`) and `takes` (`HEAD:TAKE`).

In FULL, the synthesized support value constrains the verb, so the compatible
N=1 realizations are:

```text
John pays attention .
John takes notice .
```

In NO-CONTEXT, that reuse is removed and the two cross-combinations are also
licensed.

For N independent repetitions:

- FULL licenses `2^N` realizations, all compatible;
- NO-CONTEXT licenses `4^N` combinations;
- `2^N` NO-CONTEXT combinations remain compatible.

Input fixtures are provided through `support_N10.input`; the runner defaults to
`MAX_N=7`.

## Run

From the repository root:

```bash
test/paper_support_context/run.sh /path/to/elvex
```

or, when `elvex` is on `PATH`:

```bash
test/paper_support_context/run.sh "$(command -v elvex)"
```

The runner writes per-condition `.out`, `.metrics`, `.time`, and `.status`
files. `analyze.py` combines them into `results.tsv`, including generated and
compatible counts and available Elvex instrumentation such as chart size,
forest size, saturation statistics, internal time, and peak RSS.

Runs with larger N can require a higher `MAX_ITEMS` value and substantially more
memory.
