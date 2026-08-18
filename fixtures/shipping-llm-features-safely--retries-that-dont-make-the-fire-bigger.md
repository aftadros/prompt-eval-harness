---
source_slug: shipping-llm-features-safely
source_url: https://anthonytadros.me/writing/shipping-llm-features-safely/
heading: "Retries that don't make the fire bigger"
excerpted: 2026-08-17
tampered: false
---

# Shipping an LLM feature without it going sideways
## Retries that don't make the fire bigger

Retries are where good intentions cause outages. The rule I carried over from integration work: retry only what's genuinely transient, and never in a way that piles load onto something already struggling. A 429 or a 5xx means the upstream is saturated, and three immediate retries against a saturated service turns a blip into an outage you caused. Retries here are bounded, usually at two, with exponential backoff and jitter to keep a thousand clients from resynchronizing into a thundering herd the moment the service recovers.

I sort errors into three buckets before deciding anything. Transient failures, the timeouts and 429s and 5xxs and connection resets, get the bounded backoff. Permanent failures fail fast, because retrying a 400 from a malformed request, an auth error, or a context-length overflow just spends the user's time and your money. The nasty one is the middle bucket, the 200 that came back with output you can't use. That isn't a retry candidate by default. It's a validation failure, and it routes to the fallback path, since asking the same question the same way usually gets you the same bad answer.
