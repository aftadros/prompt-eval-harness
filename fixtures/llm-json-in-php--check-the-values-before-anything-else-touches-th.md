---
source_slug: llm-json-in-php
source_url: https://anthonytadros.me/writing/llm-json-in-php/
heading: 'Check the values before anything else touches them'
excerpted: 2026-08-17
tampered: false
---

# Getting reliable JSON out of an LLM in PHP
## Check the values before anything else touches them

Decoding gives you an array of maybes. Before anything downstream sees it, I check the values against what I expect and map the result into a typed object, so the rest of the code works with a real thing instead of poking at string keys and hoping. The enum field gets checked against the allowed set rather than trusted for being a string, and a confidence that came back as 240 fails its range check right here at the boundary, not three layers down where it corrupts something.

```
$data = decodeJson($raw);

if (! Status::tryFrom($data['status'] ?? '')) {
    throw new InvalidResponse('status outside the allow-list');
}
$confidence = $data['confidence'] ?? -1;
if ($confidence < 0 || $confidence > 100) {
    throw new InvalidResponse('confidence out of range');
}

// shape and values both checked: now build a type the rest of the app can trust
$result = new Extraction(Status::from($data['status']), (int) $confidence);
```
