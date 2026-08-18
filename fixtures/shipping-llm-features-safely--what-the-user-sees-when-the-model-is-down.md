---
source_slug: shipping-llm-features-safely
source_url: https://anthonytadros.me/writing/shipping-llm-features-safely/
heading: 'What the user sees when the model is down'
excerpted: 2026-08-17
tampered: false
---

# Shipping an LLM feature without it going sideways
## What the user sees when the model is down

Every model-backed feature needs an answer to one question: what does the user see when the model is unavailable? "An error" is the lazy answer and usually the wrong one. In a retrieval-augmented assistant, retrieval and generation come apart cleanly. If generation fails, I can often still return the retrieved source documents with their citations, plus a plain note that the summarized answer isn't available right now. The person came looking for information, and the ranked passages are useful on their own. Only the synthesized paragraph on top degraded, and the note says so.

This is where the integration mindset pays off most directly. The product is a stack of capabilities rather than one monolithic call, so failure can be partial. Retrieval up with generation down means showing sources. If it's the guardrail service that's down, I fail closed and ship nothing, since an unchecked answer is worse than no answer. Which way each component fails, open or closed, is a decision I make on purpose, never one I inherit from whatever the library does by default.
