# Synthetic support-context search-space stress test

This directory contains the repeated binary support-verb experiment reported as
the **synthetic search-space stress test** in the camera-ready paper.

It is intentionally separate from `benchmark/lexical-context/`: the lexical
benchmark tests whether synthesized context enforces independently curated
support-verb choices, whereas this synthetic experiment isolates how unresolved
dependencies enlarge the search space as the same dependency is repeated.

## Construction

For one clause, the object may be lexicalized as:

- `attention` with synthesized `support:PAY`;
- `notice` with synthesized `support:TAKE`.

The available support verbs are:

- `pays` with `HEAD:PAY`;
- `takes` with `HEAD:TAKE`.

In the **FULL** grammar, the NP is operationally realized before the verb. Its
synthesized `support` value then supplies the inherited `HEAD` required by the
verb, while the surface rule remains `VP -> V NP`. The two licensed N=1 strings
are therefore:

```text
John pays attention .
John takes notice .
```

In **NO-CONTEXT**, only this reuse of the synthesized support value is removed.
The grammar also licenses the incompatible cross-combinations:

```text
John pays notice .
John takes attention .
```

## Scaling protocol

Inputs `support_N1.input` through `support_N10.input` are provided as convenient
fixtures. The runner defaults to **`MAX_N=7`**, which is the complete trace
reported in the camera-ready paper.

For N independent repetitions:

- FULL licenses `2^N` realizations, all compatible;
- NO-CONTEXT licenses `4^N` combinations;
- exactly `2^N` NO-CONTEXT combinations remain compatible;
- the compatible fraction under NO-CONTEXT is `(1/2)^N`.

The paper's N=7 snapshot is:

```text
condition     generated  valid  chart_items  packed_nodes  internal_ms  peak_RSS
FULL                128    128          437           205        7.592   11.8 MiB
NO-CONTEXT        16384    128        22069         16489     7246.538  676.9 MiB
```

Both conditions record 87 saturation passes at N=7 and a maximum of two
fixed-point passes per saturation call. Structural chart/forest counts are
deterministic for the pinned implementation; timing and RSS remain
machine-specific.

## Run

From the repository root, pass the Elvex executable explicitly:

```bash
test/paper_support_context/run.sh /path/to/elvex
```

If `elvex` is on `PATH`:

```bash
test/paper_support_context/run.sh "$(command -v elvex)"
```

The paper protocol can also be stated explicitly:

```bash
MAX_N=7 MAX_ITEMS=50000 \
  test/paper_support_context/run.sh "$(command -v elvex)"
```

The run writes, for each condition and N:

```text
*.out       generated strings
*.metrics   Elvex instrumentation
*.time      shell real/user/sys timing
*.status    process status
```

`analyze.py` combines these files into `results.tsv`, including generated and
valid counts, chart/forest timing, chart items, packed nodes, forest edges,
saturation statistics, and peak RSS.

Runs above N=7 are exploratory and are not part of the camera-ready result.
They may require a larger `MAX_ITEMS` and substantially more memory.
