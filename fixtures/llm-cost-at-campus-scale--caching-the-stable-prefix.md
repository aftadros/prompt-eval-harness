---
source_slug: llm-cost-at-campus-scale
source_url: https://anthonytadros.me/writing/llm-cost-at-campus-scale/
heading: 'Caching the stable prefix'
excerpted: 2026-08-17
tampered: false
---

# What an LLM costs at campus scale
## Caching the stable prefix

The lever with the best return for the least work is prompt caching. Most providers will cache a stable prefix of your prompt and charge a fraction of the normal input price to reuse it. In a retrieval assistant a big chunk of every prompt is identical from call to call anyway, the system instructions and the formatting rules and the guardrail preamble, with only the user's question and the retrieved passages changing between requests.

So order the prompt deliberately, stable material first, volatile last: static system prompt, then tool definitions, then retrieved context, then the question. The cached prefix can cover everything up to the first point where content varies. Get the ordering right and a high-traffic endpoint's long, repeated preamble bills at the cache rate instead of full freight, which is a real cut to effective input cost.

This is the LLM version of building an index. The query was always going to run; you're just paying to not re-read the same bytes every time. The discipline is one I recognize from databases, which is to keep the stable parts stable. The moment someone injects a timestamp or a per-user token near the top of the prompt, the cacheable prefix shrinks to nothing and the savings evaporate. Cache invalidation by accident is a real bug, and it shows up as a cost regression instead of a crash, so you only catch it if you're watching per-request cost.
