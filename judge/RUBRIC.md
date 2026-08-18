# Judge protocol

The judge is the part of an eval most likely to be wrong in a way that looks
right, so this file states the protocol it runs under and the limits placed on
it. Everything model-graded in this repo lives in this directory. That is
deliberate: you should be able to see the whole judgment surface by listing one
folder.

## One narrow yes/no question per pass

Each question in `questions.yaml` is closed, answerable from the source in hand,
and asked on its own. Not a rubric row, not a score out of ten, not a list of
dimensions to weigh. A model asked "is there a claim here the source does not
support?" is doing verification. A model asked "rate this answer 1-10" is doing
something else, and `runs/` contains the evidence of what: the scores pile up on
6, 7 and 8, and the same text scores differently on rerun.

## Verdict before explanation

`prompt.txt` requires YES or NO as the first token, reason after. A judge that
reasons first talks itself into a verdict; a judge that commits first is stuck
with one you can score. This costs a little accuracy on genuinely hard items and
buys a verdict that means the same thing every time.

## The judge is sampled, not asked once

Every judge call runs `m` times at nonzero temperature (default 5). The output is
a distribution, `p_pass`, not a verdict. A question that comes back 5-0 and a
question that comes back 3-2 are different results, and collapsing both to "pass"
throws away the part that tells you whether to trust it. The consistency bins in
the calibration report are built out of exactly this.

## What the judge may not decide

`risk: high` questions may flag, never gate. More broadly, the risk-carrying
checks in this repo are not judge questions at all. Refusal, citation validity,
canary leakage and JSON validity are deterministic checks, because those are the
cases where a wrong pass is expensive and a judge's failure mode is quiet.

The split is visible in the case files by design:

```
grep -c 'judge:' cases/*.yaml
```

If that number ever approaches the case count, the harness has drifted into
grading everything with a model, which is the thing it was built to avoid.

## Grading the grader

A judge whose agreement with a human has never been measured is a number
generator. `harness label` collects human verdicts on real outputs, blind to
model and prompt identity, and `harness calibrate` reports agreement, Cohen's
kappa with a bootstrap interval, and the confusion matrix.

The published rule of thumb was: if you and the judge disagree on a fifth of
cases, the judge is not trustworthy yet. This repo tests that rule and it does
not survive intact. Raw agreement of 80% means very different things at different
base rates, and when the pass rate is high it can be worse than chance. The
calibration report prints kappa next to raw agreement for that reason, and
`METRICS.md` carries the table.

## Bias probes

`probes.yaml` holds constructed pairs with known-correct verdicts for the three
biases this protocol is most exposed to: position (does the winner change when
the order swaps), verbosity (does padding without content flip a verdict), and
self-preference (is the judge softer on output from its own model family).
`harness judge-audit` runs them and prints each with its n.

Position bias is why the production protocol grades one output at a time against
an absolute question, rather than asking which of two answers is better.
