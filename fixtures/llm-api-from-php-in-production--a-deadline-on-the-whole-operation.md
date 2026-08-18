---
source_slug: llm-api-from-php-in-production
source_url: https://anthonytadros.me/writing/llm-api-from-php-in-production/
heading: 'A deadline on the whole operation'
excerpted: 2026-08-17
tampered: false
---

# Calling an LLM API from PHP without taking the page down
## A deadline on the whole operation

There's a trap waiting right behind the retries. Three attempts against a thirty-second timeout is, in the worst case, ninety seconds plus backoff before your fallback ever fires. You added resilience and made the bad case worse, because the user left at second eight. Retries improve the odds for a single call and do nothing at all for the person waiting on it. So I put a deadline around the entire operation, separate from the per-call timeout, and when the deadline passes I stop retrying and degrade.
