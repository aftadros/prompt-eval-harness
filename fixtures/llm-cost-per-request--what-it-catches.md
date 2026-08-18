---
source_slug: llm-cost-per-request
source_url: https://anthonytadros.me/writing/llm-cost-per-request/
heading: 'What it catches'
excerpted: 2026-08-17
tampered: false
---

# Putting a dollar figure on every model call
## What it catches

What this catches never shows up in a total. A prompt grows by accretion until one configuration screen is shipping an entire instruction manual in the system message. A refactor moves a per-request value to the top of the prompt, the cache prefix stops matching, and reuse drops to nothing while the cost climbs, with no error to page anyone about. And some spend is structural, like a retrieval feature that runs almost entirely on input tokens because you pack the context with passages and ask for two sentences back. None of it throws an exception. It spends, steadily, until someone reads cost per request by feature and the outlier is sitting in the chart.

The cache one is the worst of these, because it's invisible by design. A broken prefix doesn't crash and doesn't slow anything down; it just charges full freight for input you used to get at a discount, and the only symptom is a number on a dashboard you only have if you built it. I've watched a cache hit rate fall to zero after an innocent refactor and stay there for a while, because nothing was wrong except the bill.

The payoff is that arguments about cost stop being arguments. Nobody has to debate whether caching earns its keep or which model should be the default, because the figure that settles it is already on the dashboard, sliced by the exact thing you're about to change. And it's cheap: one more field on the request log, written next to the latency and the status code.
