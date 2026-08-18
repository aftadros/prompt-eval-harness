---
source_slug: llm-cost-at-campus-scale
source_url: https://anthonytadros.me/writing/llm-cost-at-campus-scale/
heading: 'Tokens are the row count'
excerpted: 2026-08-17
tampered: false
---

# What an LLM costs at campus scale
## Tokens are the row count

You pay per token, with input and output priced separately. Input is cheap and plentiful; output costs several times more and arrives one token at a time. A retrieval-augmented answer is input-heavy by design, because you stuff the prompt with retrieved passages, system instructions, formatting rules, maybe a few examples, and ask for a short answer back. It's easy to end up with a big prompt producing a small reply, which means almost all the spend is on the read, not the write.

That ratio is a full table scan returning one row, and the fix is the same fix: read less. Tighten retrieval so the top few passages go in instead of a long list. The system prompt gets the same audit, since it grows by accretion, every edge case earning its own paragraph, and few-shot examples can come out once the model behaves without them. It's accounting. Multiplied by daily volume, it's what moves a per-request cost from real money to a rounding error.

I don't track 'average latency' as one number. For each request I record input tokens, output tokens, and wall-clock time, then attach a dollar figure at the current per-token rates, and it's that per-request cost, bucketed by feature, that tells you whether a change helped. The monthly bill can't. It averages everything together and hides the offender.
