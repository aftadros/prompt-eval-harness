---
source_slug: shipping-llm-features-safely
source_url: https://anthonytadros.me/writing/shipping-llm-features-safely/
heading: 'Opening'
excerpted: 2026-08-17
tampered: false
---

# Shipping an LLM feature without it going sideways
## Opening

I've spent ten years wiring together systems that don't trust each other: customer SIS feeds, identity providers, payment endpoints, campus card readers. Integration work teaches you that the happy path is a rounding error. The remote thing will be slow when it matters, will eventually time out or return garbage, and when it goes down it'll be during a demo. A model call is the newest member of that family. An LLM endpoint is a third-party dependency that happens to be unusually slow and expensive, and nondeterministic besides. Every reliability instinct I picked up before I ever touched a token still applies.

These days I build the admin and configuration surface for an AI knowledge assistant, an LLM product that retrieves documents, indexes them, streams answers back, and runs guardrails over the result. The interesting engineering is almost never the prompt. It's the wrapping around the model call, which decides what a bad day at the provider feels like from inside the app.
