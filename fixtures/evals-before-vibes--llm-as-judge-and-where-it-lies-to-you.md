---
source_slug: evals-before-vibes
source_url: https://anthonytadros.me/writing/evals-before-vibes/
heading: 'LLM-as-judge, and where it lies to you'
excerpted: 2026-08-17
tampered: false
---

# Evals before vibes
## LLM-as-judge, and where it lies to you

Plenty of what I want to measure has no string match: whether an answer stayed grounded in the source it cited, whether the tone fit an end user or an internal admin, whether a refusal came out polite and specific or read like a brick wall. For those the common move is asking another model to grade the output, the pattern people call LLM-as-judge. It works and it scales to questions a regex can't touch. It'll also hand you confident garbage if you don't design around how it fails.

A judge model has biases that have nothing to do with quality. It tends to reward length, it likes answers that echo its own phrasing, and given a list of options it drifts toward the top. Ask it for a bare 1-to-10 score and you get mush that clusters around 7. So I don't. Each judge call gets one narrow yes-or-no question with the criterion spelled out, plus the source text and an instruction to check claims against that text, not against whatever the model already believes. The verdict comes before the explanation, so it isn't a rationalization of an essay the judge just wrote.

The judge itself needs grading, and that's the step people skip. It's just another model output, so it gets its own small golden set of cases I scored by hand, run through the judge, and checked for agreement. If we disagree on a fifth of them, the judge isn't trustworthy yet and its prompt needs work before it gates anything. Some inputs never get a model as the final word at all. Refusals, and anything touching access to restricted content, go through deterministic checks and human review. A judge is good at telling me where to look; signing off on cases where being wrong costs something is a different job.
