---
source_slug: shipping-llm-features-safely
source_url: https://anthonytadros.me/writing/shipping-llm-features-safely/
heading: 'Timeouts, and where the number comes from'
excerpted: 2026-08-17
tampered: false
---

# Shipping an LLM feature without it going sideways
## Timeouts, and where the number comes from

Every model call gets an explicit timeout, because SDK defaults are usually too generous or missing. The number starts with the user, though. On an interactive HTTP request, a human gives you a few seconds before deciding the thing is broken, and the server has its own ceiling before the connection dies. Work backward from that ceiling and hand the model whatever slice remains after retrieval, guardrails, and serialization take their cut.

Streaming complicates this. A streamed response can run long in total and still be fine, since tokens keep arriving, so I track two clocks: time-to-first-token and total wall time. A long total with bytes flowing is healthy, but five seconds of nothing on the wire is a stall, and I kill it. Watching the inter-token gap lets me tell a long good answer from a dead connection; the total alone can't.
