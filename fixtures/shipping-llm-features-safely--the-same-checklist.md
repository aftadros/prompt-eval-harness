---
source_slug: shipping-llm-features-safely
source_url: https://anthonytadros.me/writing/shipping-llm-features-safely/
heading: 'The same checklist'
excerpted: 2026-08-17
tampered: false
---

# Shipping an LLM feature without it going sideways
## The same checklist

Timeouts, bounded retries with jitter, a circuit breaker, graceful degradation, a kill switch, and logs you can read. That's the list I'd run against a payment integration or a campus card feed, and nothing on it is new. The one genuine addition is that a 200 can still be a failure, which is why output validation lives inside the reliability work instead of off to the side. Treat the model as the flaky, expensive remote dependency it is, design for its worst day, and the AI part stops being scary. It becomes one more integration you've made boring on purpose.
