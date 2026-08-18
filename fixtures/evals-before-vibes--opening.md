---
source_slug: evals-before-vibes
source_url: https://anthonytadros.me/writing/evals-before-vibes/
heading: 'Opening'
excerpted: 2026-08-17
tampered: false
---

# Evals before vibes
## Opening

I work on the admin and configuration side of an AI knowledge assistant, an LLM-powered product that retrieves documents, indexes them, streams answers back, and runs them past guardrails. Most of that is normal software. The prompt work isn't, because you can change one line, watch a demo answer get visibly better, ship it, and make the product worse for a hundred questions you didn't happen to type that afternoon.

A model doesn't behave like a function with a fixed contract. The same change that fixes one phrasing nudges the output distribution everywhere else. So before I trust an edit I want to know what it did across the inputs I care about, and a small eval harness is the cheap way to find out.
