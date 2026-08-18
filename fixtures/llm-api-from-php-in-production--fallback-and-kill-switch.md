---
source_slug: llm-api-from-php-in-production
source_url: https://anthonytadros.me/writing/llm-api-from-php-in-production/
heading: 'Fallback and kill switch'
excerpted: 2026-08-17
tampered: false
---

# Calling an LLM API from PHP without taking the page down
## Fallback and kill switch

Every model-backed feature I ship has a defined behavior for when the model is unavailable, and a flag that forces that behavior without a deploy. The fallback is whatever still helps with no model in the loop: a cached previous answer, a plain non-AI path, or an honest message that the smart version is off. The kill switch is a single config value, read on every request with no caching that would delay it, so when a prompt change misbehaves or costs spike I can turn the feature off in seconds and debug calmly. A kill switch you've never flipped is a guess, which is why the off state is a real, tested mode and not an error.
