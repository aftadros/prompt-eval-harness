---
id: evals-before-vibes
url: https://anthonytadros.me/writing/evals-before-vibes/
date: 2026-06-24
title: 'Evals before vibes'
---

# Evals before vibes

A prompt change can look better in the demo and still be worse across a hundred real questions. A small eval harness is how I tell the difference before I ship.

I work on the admin and configuration side of an AI knowledge assistant, an LLM-powered product that retrieves documents, indexes them, streams answers back, and runs them past guardrails. Most of that is normal software. The prompt work isn't, because you can change one line, watch a demo answer get visibly better, ship it, and make the product worse for a hundred questions you didn't happen to type that afternoon.

A model doesn't behave like a function with a fixed contract. The same change that fixes one phrasing nudges the output distribution everywhere else. So before I trust an edit I want to know what it did across the inputs I care about, and a small eval harness is the cheap way to find out.

## Vibes are a measurement, just a bad one

When an engineer says a prompt change feels better, they've already run an eval. The golden set was whatever three or four questions came to mind, the judge was their own taste at 4pm, and the sample was tiny and self-selected. Nothing got written down, so nobody can rerun it next week after the next change. Intuition is fine, it's where the change worth testing comes from. The problem is stopping there.

The discipline isn't new to me. I come from security and reliability work, and earlier in my career I remediated sensitive data across an organization's machines. That job ran on one rule. A host isn't clean because it looks clean. You scan, you get a count, you remediate, you rescan, and the count has to move. I don't see why an LLM feature deserves a looser standard.

## The golden set

The first artifact is a golden set, real inputs paired with what a good answer has to contain. Not an exact string. Most useful questions have plenty of acceptable answers, so pinning one output is fragile, and it's a lie about how the product gets used anyway. I pin checks instead. For a retrieval-augmented assistant the useful checks are concrete ones. Did the answer cite a real source document, did it stay inside what retrieval returned instead of inventing a policy, did it refuse cleanly when the corpus has no answer, did it avoid leaking content the user isn't allowed to see.

The cases come from real traffic, because the questions people asked last week beat anything I'd sit down and invent. Real users phrase things in ways you'd never think to. I keep three labeled buckets: ordinary questions that should just work, known-hard ones that exposed a bug once, and adversarial ones that try to pull the model off its guardrails. Fifty good cases beat five hundred lazy ones, and every case has to be able to fail or it's decoration.

```
# one case in the golden set
- id: refund-window-no-source
  input: "What's the refund window for enterprise plans?"
  expect:
    must_refuse: true          # corpus has no enterprise refund policy
    must_not_contain: ["30 days", "60 days"]  # don't invent a number
    must_cite: false
```

## Diffing against yesterday's run

Once the set exists the harness is a loop. Run every case through the current configuration, apply each check, write the pass and fail counts to a file, and diff that file against the last run. I mostly ignore the score and read the diff. Five cases that passed yesterday and fail today is a regression with a name on it, and I can open each one and read the new output next to the old before anyone outside the team sees it.

That reframes prompt work the way version control reframed code. The unit becomes the change and its measured effect. I keep the harness fast and boring on purpose so it runs on every prompt edit, the same way I lean on a release pipeline to tell me a build is bad before it ships rather than after a customer files a ticket. A slow eval that runs once a sprint gets skipped under deadline, right when you need it most.

- Pin the model version and decoding settings in the run record; a score with no model attached to it means nothing.
- Run each case more than once when temperature is nonzero. A check that passes 3 of 5 times is data, and a single green run hides it.
- Store every raw output alongside the pass or fail result, because when a number moves you'll want to read the text rather than rerun and hope it reproduces.
- Treat a flaky case as a finding. Either the check is too strict or the behavior really is unstable, and both are worth knowing.

## LLM-as-judge, and where it lies to you

Plenty of what I want to measure has no string match: whether an answer stayed grounded in the source it cited, whether the tone fit an end user or an internal admin, whether a refusal came out polite and specific or read like a brick wall. For those the common move is asking another model to grade the output, the pattern people call LLM-as-judge. It works and it scales to questions a regex can't touch. It'll also hand you confident garbage if you don't design around how it fails.

A judge model has biases that have nothing to do with quality. It tends to reward length, it likes answers that echo its own phrasing, and given a list of options it drifts toward the top. Ask it for a bare 1-to-10 score and you get mush that clusters around 7. So I don't. Each judge call gets one narrow yes-or-no question with the criterion spelled out, plus the source text and an instruction to check claims against that text, not against whatever the model already believes. The verdict comes before the explanation, so it isn't a rationalization of an essay the judge just wrote.

The judge itself needs grading, and that's the step people skip. It's just another model output, so it gets its own small golden set of cases I scored by hand, run through the judge, and checked for agreement. If we disagree on a fifth of them, the judge isn't trustworthy yet and its prompt needs work before it gates anything. Some inputs never get a model as the final word at all. Refusals, and anything touching access to restricted content, go through deterministic checks and human review. A judge is good at telling me where to look; signing off on cases where being wrong costs something is a different job.

## What this looks like on a normal week

The payoff is mundane, which is the point. A ticket comes in to make the assistant more concise. I write the instruction, run the harness, and conciseness improves while the grounding check drops four points, because a shorter answer stopped citing its source. Without the harness, that ships and comes back as a bug report. In the diff it was just a visible tradeoff, so I tightened the instruction and reran until conciseness and grounding both held. It's the same loop I've used for years making integrations behave. I change one thing and let the measurement decide whether it stays.

None of this needs a platform. The first version is a script, a YAML file of cases, and a results file you commit next to the code. A fancier harness can come later, once the discipline exists and you know what you're measuring. Teams that buy tooling first end up with a dashboard nobody trusts and decisions still made on vibes.

A change that feels better is still where I start. But the demo question was always going to look good; the harness is for the hundred I didn't type.
