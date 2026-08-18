---
source_slug: shipping-llm-features-safely
source_url: https://anthonytadros.me/writing/shipping-llm-features-safely/
heading: 'The kill switch'
excerpted: 2026-08-17
tampered: false
---

# Shipping an LLM feature without it going sideways
## The kill switch

Every LLM feature I ship has a flag that turns it off without a deploy. It's the cheapest insurance in the whole system, and people skip it because nothing is wrong on launch day. The day you need it, you need it within seconds, and no build-and-release cycle moves that fast. That day looks like a bad prompt change shipping, a provider suddenly returning unsafe content, a cost spike from a runaway loop, or a guardrail regression. Whichever it is, the flag drops the feature to its fallback path and you debug calmly, with the harm already stopped.

I keep the switch coarse and boring. One config flag, read on every request, with no cache in front that would delay it by ten minutes. Off means the feature behaves exactly like its graceful-degradation path. The assistant says the summarized answer is unavailable, and retrieval and the rest of the app keep working. The switch isn't an error state; it's a known, tested mode the system enters on purpose, which means I can rehearse it. A kill switch you've never flipped is a guess.
