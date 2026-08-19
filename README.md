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

`models.yaml` points the default `local` model at an OpenAI-compatible endpoint
on loopback, so nothing here needs an API key or a network connection. You do
need a server on that port serving the model id named in `models.yaml`. The
runner reads `GET /v1/models` first and refuses the run if the server is serving
something else, because an endpoint that answers for an unknown id will hand you
a complete run attributed to a model that never ran.

## How it works

**`cases/`** holds the golden set: 50 questions over the author's own published
posts, split 20 ordinary / 15 known-hard / 15 adversarial, each paired with what
a good answer has to contain. Not exact strings. Most useful questions have many
acceptable answers, and what you can pin is the check. Every case also carries a
`why` line giving the failure it guards against and a reason that failure could
actually happen on this corpus.

**`checks/`** holds the properties an answer either has or doesn't: cited a real
source document, cited only documents it was actually given, refused cleanly when
the corpus has no answer, didn't echo a canary planted by an injection, valid
JSON. There are eight, and each one is a pure function registered in a dict
literal in `checks/__init__.py`, so `grep REGISTRY` gives you the whole list.
Properties are deterministic, cheap to run, and don't drift between runs.

**`judge/`** holds everything model-graded, kept in one directory so you can see
the whole judgment surface without going looking for it. 17 of the 50 cases are
judge-routed. Each judge call asks one narrow yes-or-no question with the source
text in hand, and the reply has to start with YES or NO before any reasoning.
Each question is asked five times, so what comes back is 5-0 or 3-2 rather than a
single coin flip. No refusal case and no leak case is judge-gated. Those run on
`must_refuse` and `must_not_leak_restricted`, which are deterministic, because a
wrong answer on those costs something.

**`runs/`** holds written-down results, so any comparison can be rerun next week
after the next change. Records are append-only, and `records.py` enforces that by
refusing to overwrite a file that already exists. A record is also
self-contained: the prompt file is copied into the run directory, so editing
`prompts/v2.txt` next month cannot change what a finished run says it tested, and
`manifest.json` carries a sha256 of every case file and every fixture that went
in. The number to read is the per-case delta, not the overall average, because
the average is where a regression goes to hide.

## Reruns and statistics

The same case does not give the same answer twice, and pinning a seed does not
reliably fix that on a local server. So every case runs N times at nonzero
temperature and the result is stored as k of n. A case that passes 3 times in 5
stays on the report as a flaky case instead of being rounded to pass or fail.

The statistics run on those distributions. `harness/stats.py` is hand-rolled and
imports nothing outside the standard library:

- Wilson intervals on the pass rate
- an exact McNemar test on the paired binary outcome
- a paired bootstrap that resamples cases, not reruns
- an A/A noise floor built by splitting one prompt's own reruns in half, with
  each split delta scaled by the square root of half over N so the floor
  estimates a twin run at the arm's own rerun count rather than at half of it
- Cohen's kappa for judge-versus-human agreement
- a simulated minimum detectable effect

`tests/test_stats.py` pins each of these against reference values computed
independently of the implementation, and one test fails if a function is added to
`stats.py` without one.

Every comparison report ends with a "Can you call it?" section, and it is allowed
to say no. The template it fills in reads:

```
NOT distinguishable from rerun noise. The observed delta (<d>) is inside the
A/A noise floor (<f>), which is what running the same prompt twice looks like
on this rig. Do not ship on this delta.
```

At 50 cases, and at the discordance rate the design assumes, the smallest effect
this test can resolve at 80% power is around 0.17 absolute. A three-point
improvement is nowhere near that, so the report prints its own minimum detectable
effect next to the delta rather than leaving you to work it out. That number
comes from the sample size, and rerunning the same 50 cases does not move it.

## Case format

```yaml
- id: kh-chunk-size-trap
  input: "What chunk size does he recommend for RAG over internal docs?"
  context:
    - doc: rag-over-internal-docs--chunking-decides-what-retrieval-can-find
  checks:
    - must_cite
    - cited_ids_exist
  judge: [grounded, number_not_endorsed]
  why: >
    The post recommends a strategy and deliberately no number. "512" appears in
    the retrieved passage exactly once, as the naive counter-example being argued
    against.
  source: constructed
  added: 2026-08-17
```

This case used to carry `must_not_contain: ["512"]`. A real run failed it five
times out of five on answers that were right: the model wrote that the post
"presents a 512-token window only as an example", which is the correct reading
and contains the string. A substring check cannot tell a number being endorsed
from a number being rejected, so that question moved to the judge, and the
case file's `notes:` key records the switch.

`checks:` and `judge:` are separate keys on purpose. Which cases pay for a model
call should be visible from the outside:

```
grep -c 'judge:' cases/*.yaml
```

The bucket comes from the filename. A `bucket:` key inside a case file is
rejected at load time, so there is only one place the answer can come from.

## What it doesn't test

This harness tests what the model does with a context it was handed. It says
nothing about the retrieval filter that chose that context, or about the tool
layer and the renderer downstream. An injection case can only tell you the model
didn't repeat the planted instruction. Whether that poisoned document should have
reached the context at all is a real defense, and testing it is a different job.

## Background

The method, in long form:

- [Evals before vibes: measuring what a model actually does](https://anthonytadros.me/writing/evals-before-vibes/)
- [How to tell if a prompt change actually helped](https://anthonytadros.me/writing/did-the-prompt-change-help/)

The corpus is those two posts and nine others, chunked by the method described in
"RAG over a decade of internal docs".

## License

Code is MIT (see `LICENSE`). The `corpus/` and `fixtures/` directories hold
excerpts of the author's own published posts, included here as test fixtures, and
are not covered by the MIT grant; neither is the model-generated text under
`runs/**/outputs/`, which is derived from them. `NOTICE` states the split.
