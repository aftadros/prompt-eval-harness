# prompt-eval-harness

You change one line of a prompt, the demo answer gets visibly better, and the
product gets worse for a hundred questions you didn't happen to type that
afternoon. The fix is a fixed set of real questions run through the old prompt
and the new one, with the comparison written down before anything ships.

This is that harness, kept deliberately small. No framework: a golden set, a pile
of checks, and a runner that puts two score columns next to each other.

```
python -m harness validate                                  # no model needed
python -m harness run     --prompt prompts/v1.txt --n 5
python -m harness run     --prompt prompts/v2.txt --n 5
python -m harness compare runs/run-<A> runs/run-<B>
```

It runs against a local model out of the box. `models.yaml` points `local` at an
OpenAI-compatible endpoint on loopback, so the whole thing works with no API key
and no network.

## How it works

**`cases/`** holds the golden set: 50 questions over the author's own published
posts, split 20 ordinary / 15 known-hard / 15 adversarial, each paired with what
a good answer has to contain. Not exact strings. Most useful questions have many
acceptable answers, so what gets pinned is the check. Every case carries a `why`
line naming the failure it guards and why it is able to fail at all, because a
case that cannot fail is decoration.

**`checks/`** holds the properties an answer either has or doesn't: cited a real
source document, cited only documents it was actually given, refused cleanly when
the corpus has no answer, didn't echo a canary planted by an injection, valid
JSON. Eight of them, each a pure function, discovered through a dict literal
rather than a scan. They are deterministic, cheap, and don't drift between runs.

**`judge/`** holds everything model-graded, quarantined in one directory so the
whole judgment surface is one `ls`. 15 of the 50 cases are judge-routed. The
protocol is one narrow yes-or-no question per call, source in hand, verdict
before explanation, sampled five times so a verdict is a distribution rather than
a coin flip. Refusals and leak checks are never judge-gated: those are the cases
where being wrong costs something, and a judge's failure mode is quiet.

**`runs/`** holds written-down results, so any comparison can be rerun next week
after the next change. Records are append-only and self-contained: the prompt is
copied in rather than referenced, every raw output is stored, and the manifest
pins a hash of every input. The number to read is the per-case delta, not the
overall average, because the average is where a regression goes to hide.

## The part most eval harnesses skip

Reruns are the mechanism, not seeds. Every case runs N times at nonzero
temperature and the result is stored as k of n, so a case that passes 3 times in
5 stays visible as a flaky case instead of being rounded into a verdict.

That distribution is what the statistics run on. `harness/stats.py` is
stdlib-only and hand-rolled: Wilson intervals, an exact McNemar test on the
paired binary outcome, a paired bootstrap that resamples cases rather than
reruns, an empirical A/A noise floor built by splitting one prompt's own reruns
in half, Cohen's kappa for judge-versus-human agreement, and a simulated minimum
detectable effect. Every function is pinned in `tests/` against reference values
computed independently of the implementation.

The comparison report ends with a section called "Can you call it?" that is not
optional and is allowed to say no:

```
NOT distinguishable from rerun noise. The observed delta (+0.020) is inside the
A/A noise floor (0.043), which is what running the same prompt twice looks like
on this rig. Do not ship on this delta.
```

At 50 cases this harness cannot detect a three-point improvement, and it prints
the number it can detect instead of leaving the reader to assume. That limit is
a property of the sample size, not a flaw to be worked around, and stating it is
the difference between a measurement and a decoration.

## Case format

```yaml
- id: kh-chunk-size-trap
  input: "What chunk size does he recommend for RAG over internal docs?"
  context:
    - doc: rag-over-internal-docs--chunking-decides-what-retrieval-can-find
  checks:
    - must_not_contain: ["512"]
    - must_cite
    - cited_ids_exist
  judge:
    - grounded
  why: >
    The post recommends a strategy and deliberately no number. "512" appears in
    the retrieved passage exactly once, as the naive counter-example being argued
    against.
  source: constructed
  added: 2026-08-17
```

`checks:` and `judge:` are separate keys on purpose. Which cases pay for a model
call should be visible from the outside:

```
grep -c 'judge:' cases/*.yaml
```

The bucket comes from the filename, never from a key in the file. One source of
truth.

## What it doesn't test

This harness tests model behavior given a context. It does not test the retrieval
filter that decided what entered the context, the tool layer, or the renderer on
the way out. The injection cases can tell you the model didn't repeat a planted
instruction; they cannot tell you the poisoned document should never have been
retrieved. Those are real defenses and they are somebody else's test.

## Background

The method, in long form:

- [Evals before vibes: measuring what a model actually does](https://anthonytadros.me/writing/evals-before-vibes/)
- [How to tell if a prompt change actually helped](https://anthonytadros.me/writing/did-the-prompt-change-help/)

The corpus is those posts and nine others, chunked by the method one of them
describes.

## License

Code is MIT (see `LICENSE`). The `corpus/` and `fixtures/` directories hold
excerpts of the author's own published posts, included here as test fixtures, and
are not covered by the MIT grant.
