---
source_slug: llm-json-in-php
source_url: https://anthonytadros.me/writing/llm-json-in-php/
heading: 'One repair attempt'
excerpted: 2026-08-17
tampered: false
---

# Getting reliable JSON out of an LLM in PHP
## One repair attempt

When the parse or the validation fails, the model gets one more try with the failure attached, because often it just needs to be told what it got wrong. Feed back the specific error and ask again. If the second answer is still bad, fall back to whatever the feature does without the extraction rather than keep hammering the endpoint. A model that missed twice on the same input isn't going to be argued into it on the fifth attempt, and you're paying full price for every one of them.

None of this is much code. The schema mode does the heavy lifting, and everything after it is insurance for the times it slips, which on a busy endpoint is more often than the marketing implies. What the extra lines buy is the thing the demos pretend you already have: a response your PHP code can act on, with no layer of array_key_exists and silent shrugs holding it up.
