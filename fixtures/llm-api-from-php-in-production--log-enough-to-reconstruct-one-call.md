---
source_slug: llm-api-from-php-in-production
source_url: https://anthonytadros.me/writing/llm-api-from-php-in-production/
heading: 'Log enough to reconstruct one call'
excerpted: 2026-08-17
tampered: false
---

# Calling an LLM API from PHP without taking the page down
## Log enough to reconstruct one call

Nondeterminism is what makes these bugs miserable, and logging is how you claw the ground back. For every call I record a request id, the model and version, input and output token counts, latency split into time-to-first-token and total, which retry attempt this was, whether the breaker was open, and which path served the response: model, fallback, or kill switch. I don't log secrets, and I treat the prompt and the user content as sensitive, because on this product they often are. With those fields an LLM incident stops being a vibe and becomes an ordinary production incident. You pull the trace, you see the timeout on attempt two with the breaker half-open, and you know what happened.

> Treat the model as the flaky, expensive remote dependency it is, design for its worst day, and the AI part stops being scary. It's one more integration made boring on purpose.

Nothing here needed Python. Two timeouts, transient-only retries with jitter, a deadline on the operation, a circuit breaker, output you validate instead of trusting, a fallback, a kill switch, logs you can read: it's the checklist I'd run on a payment integration or a campus card feed, with one extra line for the fact that a successful response can still be a failure.
