---
source_slug: shipping-llm-features-safely
source_url: https://anthonytadros.me/writing/shipping-llm-features-safely/
heading: 'Log enough to reconstruct the call'
excerpted: 2026-08-17
tampered: false
---

# Shipping an LLM feature without it going sideways
## Log enough to reconstruct the call

Nondeterminism makes LLM bugs miserable, and logging is how you claw back ground. When a user says the assistant gave a strange answer, I need to rebuild that exact call. So I log the request id, the model and version, token counts, latency split into time-to-first-token and total, which retry attempt this was, whether the breaker was open, and which path served the response: model, fallback, or kill switch. The retrieved document ids that went into the context get logged too. Raw secrets never do, and the prompt and the user's content get handled as sensitive data, with the care I gave PII on earlier identity and access projects, because in this product they often are PII.

Token counts and latency are the new query plan. They're the numbers that tell you a prompt change doubled your context size, that one document type is blowing the budget, or that p99 latency is creeping because retrieval got slower and the model didn't. Miss them and you're debugging a nondeterministic system by vibes, which is to say guessing. With them in place, an LLM incident looks like any other production incident: you pull the trace, see the timeout on attempt two with the breaker half-open, and know what happened.
