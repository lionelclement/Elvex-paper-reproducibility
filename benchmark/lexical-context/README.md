# Lexical-context ablation

This benchmark evaluates synthesized-context reuse on lexical dependencies taken
from the English Elvex grammar in `Elvex/test/en-llm`. It complements the
synthetic `2^N`/`4^N` support-verb stress test used in the paper: the synthetic
test isolates search-space growth, whereas this benchmark asks whether the same
mechanism controls independently curated lexical choices.

## Research question

The benchmark tests one realization-dependent property: **support-verb
selection by a predicative noun**.

For example, the semantic input identifies `WARNING`, but does not prescribe
`GIVE`. Lexicalizing the predicative noun `warning` synthesizes
`support:[HEAD:GIVE]`. In the FULL condition, that synthesized structure is
reused as the inherited specification of the verb, licensing a realization such
as `John gives a warning`.

The experiment compares three conditions:

- **FULL** — the semantic input contains the predicative-noun head only. The
  support specification produced by nominal lexicalization is reused to
  constrain the verb.
- **NO-CONTEXT** — the same noun is lexicalized, but its synthesized support
  specification is deliberately ignored. The verb is selected independently
  from the support-verb inventory represented by the benchmark.
- **PRE-SPECIFIED** — the correct support specification is supplied in the
  input from the start. This is the over-specified control condition.

The central comparison is therefore FULL versus PRE-SPECIFIED versus
NO-CONTEXT. If synthesized context provides the intended control, FULL should
behave like PRE-SPECIFIED even though its input is less specified, while
NO-CONTEXT should retain the valid realization and additionally license
cross-frame noun/support combinations.

This is not an asymptotic-complexity experiment.

## Lexical sample and provenance

The committed `cases.tsv` contains 12 curated `Oper1` predicative-noun
constructions and nine distinct support verbs:

`ADOPT`, `GIVE`, `HAVE`, `IMPOSE`, `MAKE`, `OFFER`, `PAY`, `PROVIDE`, and
`TAKE`.

Examples in the source data include:

- `WARNING` → `GIVE`
- `FEAR` → `HAVE`
- `MEMORY` → `HAVE`
- `PROHIBITION` → `IMPOSE`
- `CRITIQUE` → `OFFER`
- `RATIONALE` → `PROVIDE`
- `STANCE` → `TAKE`
- `VIEWPOINT` → `ADOPT`
- `DIVIDEND` → `PAY`
- `DONATION` → `MAKE`

The snapshot is extracted from the following files in `Elvex/test/en-llm`:

- `en-lexical-functions.tsv`
- `en-predicative-nouns.tsv`
- `en-support-verb-profiles.tsv`
- `en.morpho`

The extraction keeps unique curated `Oper1` relations with an explicit
predicative-noun profile, an indefinite nominal predicate, and an overt
prepositional second argument. These restrictions provide a homogeneous sample
while preserving independently curated lexical differences.

`cases.tsv` also records preposition, semantic-valency, argument restriction,
Aktionsart, fixedness, and support-verb profile information. These properties
are **not** ablated in the current experiment. The present benchmark isolates
support-verb propagation only; other dependencies can be evaluated separately
without conflating several effects in one test.

The English grammar intentionally leaves `a/an` selection to morphology or
post-processing. The extractor therefore keeps consonant-initial nouns and uses
a fixed `a`; article selection is not treated as a context effect.

## Requirements

The benchmark requires:

- Python 3;
- a built Elvex executable;
- this `Elvex-paper-reproducibility` checkout.

The benchmark runner locates the Elvex executable in this order:

1. `--elvex PATH`;
2. `$ELVEX_BIN`;
3. `elvex` on `$PATH`.

An explicit executable can therefore be supplied with:

```bash
bash benchmark/lexical-context/run.sh --elvex /path/to/elvex
```

## Verify the lexical snapshot

From the root of `Elvex-paper-reproducibility`, verify that the committed cases
still match a sibling Elvex checkout:

```bash
python3 benchmark/lexical-context/extract_cases.py \
  --elvex-root ../Elvex \
  --check
```

Expected output for the version used in the paper:

```text
OK: 12 lexical-context cases
```

If `cases.tsv` is intentionally refreshed from a newer Elvex checkout, omit
`--check`:

```bash
python3 benchmark/lexical-context/extract_cases.py \
  --elvex-root ../Elvex
```

A changed snapshot should be reviewed before using it to reproduce the reported
numbers.

## Smoke test

Run the first three cases with the complete nine-support lexical inventory:

```bash
bash benchmark/lexical-context/run.sh --limit 3
```

`--limit` limits only the number of evaluated cases. It does **not** reduce the
support-verb inventory, so the smoke test and the full experiment compare the
same lexical alternatives.

Expected structural counts are:

```text
cases: 3
condition       generated  valid  spurious  valid_%
FULL                    3      3         0  100.000
NO-CONTEXT             27      3        24   11.111
PRE-SPECIFIED           3      3         0  100.000
```

The printed `wall_ms` values are machine- and run-dependent and are therefore
not part of these expected counts.

## Full experiment

Run all 12 cases:

```bash
bash benchmark/lexical-context/run.sh
```

For the committed lexical snapshot, the expected structural result is:

```text
cases: 12
condition       generated  valid  spurious  valid_%
FULL                   12     12         0  100.000
NO-CONTEXT            108     12        96   11.111
PRE-SPECIFIED          12     12         0  100.000
```

A reference run produced wall-clock totals of approximately 22.950 ms for FULL,
28.224 ms for NO-CONTEXT, and 18.846 ms for PRE-SPECIFIED. These timings are
reported only as an example of one run; they should not be expected to match on
a different machine or build.

The structural interpretation is the important result:

- FULL: 12/12 generated outputs are lexically compatible;
- PRE-SPECIFIED: 12/12 generated outputs are lexically compatible;
- NO-CONTEXT: all 12 valid realizations remain available, but 96 additional
  noun/support combinations are licensed.

Thus FULL obtains the same lexical control as PRE-SPECIFIED while allowing the
semantic input to remain underspecified until nominal lexicalization determines
the support verb.

Validate the committed structural snapshot without rerunning Elvex:

```bash
python3 benchmark/lexical-context/check_results.py
python3 -m unittest discover -s benchmark/lexical-context/tests -v
```

The checker verifies the immutable `reference-results.tsv` snapshot: the
complete 12-case/three-condition design, the nine-verb
inventory, case-level FULL/PRE-SPECIFIED equivalence, retention of every valid
output under ablation, and the reported 96 incompatible NO-CONTEXT outputs.
Machine-dependent timings are intentionally excluded from this static check.

The top-level validator performs both static and live checks. When `elvex` is
available on `PATH`, it reruns all 36 condition/case combinations into a
temporary result file and validates that fresh file against the same
confirmatory invariants:

```bash
python3 validate_repo.py --require-elvex
```

The committed `reference-results.tsv` is never overwritten by repository
validation.

## Repeated timing protocol

The structural counts above are deterministic. To measure timing variability,
run 30 measured repetitions after two warm-up repetitions:

```bash
python3 benchmark/lexical-context/run_repeated.py \
  --warmups 2 \
  --repeats 30
```

The runner cycles through all six permutations of the three conditions so that
no condition systematically runs first or last. Every measured repetition is
validated against the structural hypotheses before its timing is retained.

It writes three ignored, machine-specific files:

- `repeated-results.tsv`: condition totals for every repetition;
- `timing-summary.tsv`: median, quartiles, IQR, p90, p95, and maximum;
- `timing-environment.tsv`: platform, Python, executable, commit metadata, and
  run protocol.

These measurements sum the wall-clock durations of the 12 Elvex invocations in
each condition. They do not include Python setup or result validation.

## Heterogeneous composition stress test

The original paper stress test repeats one ambiguous construction. The
heterogeneous test instead composes distinct predicative-noun constructions.
For every size from one to four, `heterogeneous-panels.tsv` contains nine cyclic
panels drawn from one representative of each support verb. Within a panel, no
support verb is repeated; across the nine rotations, every support appears
exactly `N` times. This gives a balanced deterministic design rather than a
single favorable selection.

FULL reuses the support synthesized by each noun. NO-CONTEXT keeps the same
noun inputs and the same nine-verb inventory but selects each verb
independently. Therefore a panel of size `N` must have one FULL output and
`9^N` NO-CONTEXT outputs, exactly one of which is the compatible sequence.

Run a small smoke test first:

```bash
python3 benchmark/lexical-context/run_heterogeneous.py \
  --max-n 2 \
  --panels-per-n 1
```

Run the complete 36-panel experiment and validate the generated result:

```bash
python3 benchmark/lexical-context/run_heterogeneous.py --max-n 4
python3 benchmark/lexical-context/check_heterogeneous_results.py \
  --require-complete
```

Expected aggregate structural counts are:

| Condition | N | Panels | Licensed | Compatible | Incompatible | Compatible % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| FULL | 1--4 | 9 per N | 9 per N | 9 per N | 0 | 100.000 |
| NO-CONTEXT | 1 | 9 | 81 | 9 | 72 | 11.111 |
| NO-CONTEXT | 2 | 9 | 729 | 9 | 720 | 1.235 |
| NO-CONTEXT | 3 | 9 | 6,561 | 9 | 6,552 | 0.137 |
| NO-CONTEXT | 4 | 9 | 59,049 | 9 | 59,040 | 0.015 |

The generated `heterogeneous-results.tsv` also records chart, forest,
saturation, internal-time, and RSS fields when the installed Elvex executable
emits `ELVEX_METRICS`. Structural validity and output counts do not depend on
that optional instrumentation.

Both extended experiments can also be run through the repository validator:

```bash
python3 validate_repo.py --require-elvex --run-extended-context
```

See `EXPERIMENT_PROTOCOL.md` for the confirmatory hypotheses, acceptance
criteria, timing protocol, relationship to the synthetic stress test, and the
recommended multi-phenomenon follow-up suite.

## Output file

Each run writes an ignored local result file:

```text
benchmark/lexical-context/results.tsv
```

The paper's immutable reference snapshot is committed separately as
`reference-results.tsv`. This prevents an ordinary rerun from silently changing
the evidence used by the repository's static validation.

There is one row per case and condition. The columns are:

- `condition` — `FULL`, `NO-CONTEXT`, or `PRE-SPECIFIED`;
- `case_id` — stable identifier from `cases.tsv`;
- `predicate` — predicative-noun semantic head;
- `expected` — lexically compatible reference realization;
- `unique_outputs` — number of distinct outputs generated for that case;
- `valid_outputs` — whether the expected realization is present (0 or 1 in the
  current benchmark);
- `spurious_outputs` — generated outputs other than the expected realization;
- `valid_fraction` — valid outputs divided by unique outputs for that case;
- `wall_ms` — wall-clock time for that invocation of Elvex;
- `metric_lines` — number of `ELVEX_METRICS` records emitted by the Elvex build.

The summary printed by the runner sums `unique_outputs`, `valid_outputs`, and
`spurious_outputs` across cases. Consequently, `108` in NO-CONTEXT means 108
case-level distinct realizations in total, not 108 globally unique strings.

The runner exits with an error if FULL or PRE-SPECIFIED fails to produce exactly
one valid output and zero spurious outputs for any case.

## Running selected conditions

Conditions can be run separately, for example:

```bash
bash benchmark/lexical-context/run.sh \
  --conditions FULL,PRE-SPECIFIED
```

or:

```bash
bash benchmark/lexical-context/run.sh \
  --conditions NO-CONTEXT
```

A different case snapshot or result path can be supplied directly to
`run_benchmark.py`; use `--help` to list the available options:

```bash
python3 benchmark/lexical-context/run_benchmark.py --help
```

## Relation to the synthetic stress test

This benchmark and the synthetic support-verb experiment answer different
questions.

The synthetic experiment deliberately repeats independent binary dependencies
and is useful for measuring controlled growth of the chart and shared forest.
The lexical-context benchmark instead uses independently curated lexical
relations from `en-llm` and asks whether synthesized-context reuse prevents
lexically incompatible cross-frame realizations.

The lexical benchmark should therefore be read as the linguistically grounded
ablation, and the synthetic experiment as a separate search-space stress test.

## Troubleshooting

If the shell reports `permission denied` for `run.sh`, either invoke it through
`bash` as shown above or restore the executable bit:

```bash
chmod +x benchmark/lexical-context/run.sh
```

If the runner reports that it cannot find Elvex, use `--elvex` or set
`ELVEX_BIN`:

```bash
export ELVEX_BIN=~/Elvex/bin/elvex
bash benchmark/lexical-context/run.sh
```

If snapshot verification reports that `cases.tsv` is out of date, first check
that the Elvex checkout corresponds to the commit intended for the
reproducibility package before regenerating the file.
