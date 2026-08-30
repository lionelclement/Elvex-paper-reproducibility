# Benchmarks

The paper uses two maintained benchmark pipelines:

- `e2e/`: E2E/GEM closed-domain realization and slot-preservation evaluation.
- `webnlg/`: WebNLG v2.1 local RDF realization evaluation.

Both directories contain the scripts and hand-maintained resources needed to
recreate their experiments. Downloaded corpora and generated artifacts are
excluded from Git and are rebuilt by the documented commands.

The former `benchmark-E2E/` development directory has been removed. It mixed
superseded E2E, WebNLG, lexical-probe, and exploratory resources and is not part
of the reproducibility protocol reported in the paper.
