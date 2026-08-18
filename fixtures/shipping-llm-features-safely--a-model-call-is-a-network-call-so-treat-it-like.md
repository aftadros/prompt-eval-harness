---
source_slug: shipping-llm-features-safely
source_url: https://anthonytadros.me/writing/shipping-llm-features-safely/
heading: 'A model call is a network call, so treat it like one'
excerpted: 2026-08-17
tampered: false
---

# Shipping an LLM feature without it going sideways
## A model call is a network call, so treat it like one

The first mistake people make moving from a notebook to production is treating the SDK call like a local function. It's an HTTP request to a busy service, one that can take 30 seconds, return a 5xx, or hang forever. Framed that way, you already own a decade of patterns for it: timeouts, retries, circuit breakers, bulkheads, fallbacks. There's nothing AI-specific in that list. It's the checklist I'd run on any integration to a system I don't control.

What's different is the cost and the shape of failure. When a database read fails, it fails cheap and obvious. A model call can eat 25 seconds and a pile of tokens, then hand back confident nonsense that passes your JSON parse. So the wrapping has to cover outright failure and also the 200 with output you can't use. Reliability and output validation end up being one surface here, and I treat them together.
