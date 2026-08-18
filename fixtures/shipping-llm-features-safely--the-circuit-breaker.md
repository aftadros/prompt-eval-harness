---
source_slug: shipping-llm-features-safely
source_url: https://anthonytadros.me/writing/shipping-llm-features-safely/
heading: 'The circuit breaker'
excerpted: 2026-08-17
tampered: false
---

# Shipping an LLM feature without it going sideways
## The circuit breaker

When the model endpoint is genuinely down, the worst thing a service can do is keep trying, so that every user waits out the full timeout before seeing a failure. That converts a provider outage into a latency disaster across the whole app. A circuit breaker fixes it. Past a threshold of failures in a window, the breaker opens and calls fail immediately for a cool-down period instead of hanging. Every so often it lets one probe request through; if the probe succeeds, it closes and traffic resumes.

The payoff shows during the outage itself. Users get an instant, honest "this isn't available right now" in place of a 25-second spinner that ends in the same place. Fast failure also protects your own thread pools and connection limits from filling with doomed requests, which is the usual mechanism when one slow dependency drags down everything sharing the process. On a PHP and Kubernetes platform, where a stuck worker is a worker that isn't serving anyone else, I don't consider that protection optional.
