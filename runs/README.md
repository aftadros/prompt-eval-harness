# runs

Every record here is append-only and self-contained. `records.py` refuses to
write into a path that already exists, and the only file regenerated in place is
`report.md`, which is derived and holds no information of its own.

Three record types, told apart by prefix:

- **`run-<date>-<sha12>-<seq>/`** one prompt over the case set
- **`cmp-<date>-<sha12>-<seq>/`** one A/B comparison of two runs
- **`cal-<date>-<sha12>-<seq>/`** one judge-versus-human calibration

The `sha12` is the first twelve hex characters of a sha256 over the canonicalized
manifest, so two runs with identical inputs share it. The date and sequence exist
because temperature is nonzero on purpose: identical inputs legitimately produce
different runs, and collapsing them onto one directory would lose data rather
than deduplicate it.

## What a run record contains

```
manifest.json          every input, hashed: prompt, case files, each fixture,
                       model requested AND model the server reported, decoding,
                       rerun count, harness commit, python version
prompt.txt             the prompt copied in, not referenced
outputs/<case>/rN.txt  every raw generation, verbatim
results.jsonl          one row per (case, rerun): every check with its evidence
summary.json           per (case, check): {"passes": k, "n": n}
report.md              derived
```

`summary.json` stores k and n rather than a verdict. That is the load-bearing
choice in the whole layout: a case that passed 3 times in 5 is neither a passing
case nor a failing one, and collapsing it at write time destroys the only signal
that says so. Everything downstream derives what it needs, and "flaky" is
computed as 0 < k < n rather than stored.

## Reading one

Start with the per-case table in `report.md`, which sorts regressions first. The
aggregate is below it on purpose.

A partial record, one whose run died mid-batch, has `manifest.json` and some
`outputs/` but no `summary.json`. Outputs are written the moment each generation
arrives, so a crash costs one call rather than the batch, at the price of leaving
these behind. They are not runs and nothing will compare against them.

Three partial records from the first collection night (2026-08-18) are kept with
an `aborted.txt` naming what stopped each one. Deleting them would be tidier
and less true.

## Records that predate a fix

The verdict paragraph in a `cmp` record is templated code, and the template has
changed. `cmp-2026-08-18-54c5ec446d1c-1` prints "about nan" where the
detectability limit belongs, from before the report guarded that value; its
`-2` twin over the same two runs was written after the fix. Comparisons written
before 2026-08-19 can also carry the sentence "every one of the N discordant
pairs went the same way" on a mixed split, which was wrong; `compare.json`
carries `harness_git_sha` from that date on so the code behind a verdict is
part of the record, and `report.md` recomputes the verdict from the stored
numbers on regeneration. Old `stats.json` files are left as written.

