# Lexical-context ablation

This directory reproduces the support-verb ablation reported in the paper. It
tests whether a lexical constraint produced during realization can constrain a
later realization decision without being supplied in the initial semantic
input.

## Experimental design

The benchmark uses the dedicated English `en-oper1` resource in
`resources/en-oper1/`. It contains 12 curated `Oper1` predicative-noun relations
covering nine support verbs:

`ADOPT`, `GIVE`, `HAVE`, `IMPOSE`, `MAKE`, `OFFER`, `PAY`, `PROVIDE`, and
`TAKE`.

For example, the semantic input identifies `WARNING` but does not prescribe
`GIVE`. Lexicalizing `warning` synthesizes `support:[HEAD:GIVE]`.

The three conditions differ only in access to that support specification:

- **FULL** — the noun's synthesized support value is reused to constrain the
  verb;
- **NO-CONTEXT** — the synthesized support value is ignored and the verb ranges
  over the same nine-verb inventory;
- **PRE-SPECIFIED** — the correct support value is supplied in the input from
  the start.

The experiment isolates support-verb propagation. It does not evaluate lexical
acquisition or other realization-dependent phenomena.

## Lexical resource and case snapshot

The canonical source resource is:

```text
benchmark/lexical-context/resources/en-oper1/
```

`extract_cases.py` normalizes it into the committed `cases.tsv` snapshot. Verify
that the snapshot matches the resource with:

```bash
python3 benchmark/lexical-context/extract_cases.py --check
```

Expected output:

```text
OK: 12 lexical-context cases
```

See `resources/en-oper1/README.md` for the resource files.

## Expected structural result

Across the 12 cases:

- FULL licenses 12 compatible realizations and no incompatible realization;
- PRE-SPECIFIED licenses the same 12 compatible realizations;
- NO-CONTEXT preserves those 12 compatible realizations but licenses eight
  additional support verbs per case, for 108 licensed realizations overall and
  96 incompatible noun/support combinations.

Equivalent aggregate counts are:

```text
condition       licensed  compatible  incompatible
FULL                  12          12             0
PRE-SPECIFIED         12          12             0
NO-CONTEXT           108          12            96
```

## Requirements

- Python 3;
- a working `elvex` executable;
- this repository checkout.

The runner locates Elvex in this order:

1. `--elvex PATH`;
2. `$ELVEX_BIN`;
3. `elvex` on `$PATH`.

## Run the ablation

From the repository root:

```bash
bash benchmark/lexical-context/run.sh
```

To supply Elvex explicitly:

```bash
bash benchmark/lexical-context/run.sh --elvex /path/to/elvex
```

A short smoke test can be run with:

```bash
bash benchmark/lexical-context/run.sh --limit 3
```

`--limit` reduces the number of cases only; the nine-support inventory remains
unchanged.

The local result is written to:

```text
benchmark/lexical-context/results.tsv
```

The committed structural snapshot used for static verification is
`reference-results.tsv`.

## Validate the structural result

Without rerunning Elvex:

```bash
python3 benchmark/lexical-context/check_results.py
python3 -m unittest discover -s benchmark/lexical-context/tests -v
```

When Elvex is available, the repository-level validator reruns the 12 cases in
all three conditions into a temporary result file and checks the same
invariants:

```bash
python3 validate_repo.py --require-elvex
```

## Reproduce the timing measurements

The paper reports 30 measured repetitions after two warm-ups, with the order of
the three conditions balanced across runs:

```bash
python3 benchmark/lexical-context/run_repeated.py \
  --warmups 2 \
  --repeats 30
```

For each repetition, the reported time is the sum of the 12 Elvex invocations
for that condition. Python setup and result validation are not included.

The reference timing snapshot reports:

| Condition | Runs | Median (ms) | p95 (ms) |
| --- | ---: | ---: | ---: |
| FULL | 30 | 18.480 | 19.920 |
| PRE-SPECIFIED | 30 | 18.931 | 19.979 |
| NO-CONTEXT | 30 | 26.298 | 27.824 |

Validate the committed timing evidence with:

```bash
python3 benchmark/lexical-context/check_timing_results.py
```

The committed files are:

```text
reference-repeated-results.tsv
reference-timing-summary.tsv
reference-timing-environment.tsv
```

Fresh timing runs write machine-specific local files with the corresponding
unprefixed names.

## Result columns

`results.tsv` / `reference-results.tsv` contain one row per case and condition.
The main columns are:

- `condition` — FULL, NO-CONTEXT, or PRE-SPECIFIED;
- `case_id` — stable identifier from `cases.tsv`;
- `predicate` — predicative-noun semantic head;
- `expected` — compatible reference realization;
- `unique_outputs` — number of distinct outputs generated for the case;
- `valid_outputs` — number of compatible outputs;
- `spurious_outputs` — generated outputs other than the expected realization;
- `valid_fraction` — compatible outputs divided by distinct outputs;
- `wall_ms` — wall-clock time for the Elvex invocation.

The summary printed by the runner sums counts across cases. Thus 108 for
NO-CONTEXT means 108 case-level realizations in total, not 108 globally unique
strings.
