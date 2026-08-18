---
source_slug: llm-cost-at-campus-scale
source_url: https://anthonytadros.me/writing/llm-cost-at-campus-scale/
heading: 'Streaming and retries'
excerpted: 2026-08-17
tampered: false
---

# What an LLM costs at campus scale
## Streaming and retries

Streaming doesn't make the model cheaper or the generation faster. You pay for the same output tokens and the model spends the same time producing them. What changes is when the user sees the first word: time-to-first-token drops to a fraction of a second, and a long answer stops feeling frozen.

That matters because perceived latency is what drives retries. Somebody waits eight seconds on a blank screen, hits the button again, and now you've paid for two generations to answer one question. Streaming kills that failure mode, so I count it as a cost control even though it touches no token price directly. It also changes the timeout math: an answer that's slow but visibly making progress can keep its connection open, instead of getting failed and turning into a retry you also pay for.
