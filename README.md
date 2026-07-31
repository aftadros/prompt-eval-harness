<!-- DRAFT for Anthony's voice-pass. Nothing here is published. Code is yours to write. -->

# prompt-eval-harness

You change one line of a prompt, the demo answer gets visibly better, and the
product gets worse for a hundred questions you didn't happen to type that
afternoon. The fix is a fixed set of real questions run through the old prompt
and the new one, with the comparison written down before anything ships.

This is that harness, kept deliberately small. No framework — a golden set, a
pile of checks, and a runner that puts two score columns next to each other.

## How it works

**`cases/`** holds the golden set: real inputs, seeded from production and
salted with every reported bad answer, each paired with what a good answer has
to contain. Not exact strings — most useful questions have many acceptable
answers. What you can pin is the check.

**`checks/`** holds the properties an answer either has or doesn't: cited a
real source document, stayed inside what retrieval returned, refused cleanly
when the corpus has no answer, valid JSON. Properties are deterministic, cheap
to run, and don't drift between runs. Model-graded rubrics are reserved for
the answers that genuinely need judgment.

**`runs/`** holds written-down results, so any comparison can be rerun next
week after the next change. The number to read is the per-case delta, not the
overall average — the average is where a regression goes to hide.

## Case format (draft)

```yaml
id: corpus-has-no-answer
input: "What's the refund policy for summer housing?"
why: "Model invented a policy when the corpus had none."
checks:
  - refuses_cleanly
  - cites_no_source
```

## Background

The method, in long form:

- [Evals before vibes: measuring what a model actually does](https://anthonytadros.me/writing/evals-before-vibes/)
- [How to tell if a prompt change actually helped](https://anthonytadros.me/writing/did-the-prompt-change-help/)

## License

Code is MIT (see `LICENSE`). The `corpus/` and `fixtures/` directories hold
excerpts of the author's own published posts, included here as test fixtures,
and are not covered by the MIT grant.
