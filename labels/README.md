# labels

`human-labels.jsonl` lands here, append-only, one row per (output, question).

It is empty, and that is a real gap rather than a placeholder. `harness
calibrate` refuses to run without labels instead of reporting agreement against
nothing:

```
no human labels yet. `python -m harness label <run>` first.
Calibration without labels is the step everyone skips, and skipping it is
what makes a judge a number generator.
```

Labels are keyed by the sha256 of the output text, not by case id and rerun
index. That is deliberate: a label attaches to the exact string a human read, so
it joins to any judge verdict on that same string no matter which run produced
it, and re-running the judge later does not orphan the labeling work.

The labeling protocol is in `design/CORPUS.md`. Two things about it are worth
knowing before reading any agreement number that eventually appears here:

- **Blind to model and prompt identity, and blind to the judge's verdict.**
  `harness label` shuffles outputs and shows them by hash. Bucket is not blinded,
  because adversarial questions announce themselves and pretending otherwise
  would be theater.
- **Single rater.** A self-labeled set supports judge-versus-one-human agreement
  and says nothing about human-human reliability. Any kappa reported off this
  file has to be worded that way.
