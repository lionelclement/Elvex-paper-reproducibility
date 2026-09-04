# Benchmarks used in the paper

The camera-ready paper reports three maintained benchmark pipelines. They test
different questions and should not be conflated.

## `lexical-context/` — direct mechanism ablation

FULL / NO-CONTEXT / PRE-SPECIFIED comparison on 12 curated `Oper1`
predicative-noun constructions defined in the dedicated `en-oper1` resource,
covering nine support verbs. The resource is committed in
`lexical-context/resources/en-oper1/`.

The camera-ready structural result is:

```text
condition       licensed  compatible  spurious  compatible_%
FULL                  12          12         0         100.0
PRE-SPECIFIED         12          12         0         100.0
NO-CONTEXT           108          12        96          11.1
```

This is the direct empirical test of synthesized support-verb context reuse.
The directory also contains the repeated timing protocol and heterogeneous
composition stress test.

## `e2e/` — closed-domain coverage and input preservation

The full E2E/GEM test split is used as a controlled realization benchmark. The
training split supplies the lexical inventory; the test split is used for
evaluation only.

The camera-ready result is 1,847/1,847 inputs generated and 11,428/11,428 input
slots preserved (`100%` coverage, `100%` slot accuracy, `0%` SER).

## `webnlg/` — local RDF realization

The WebNLG v2.1 official test split is restricted to entries containing one to
three modified RDF triples. The paper reports local generation coverage and
oracle-style best-of-forest reference overlap. It does **not** claim a full
RDF-to-text pipeline, leaderboard comparability, or phenomenon-specific
structural accuracy.

Each benchmark directory contains its exact data provenance, requirements,
commands, generated artifacts, and expected paper-level results.

Downloaded corpora, generated build products, and virtual environments are
normally excluded from Git and are recreated by the documented commands.
