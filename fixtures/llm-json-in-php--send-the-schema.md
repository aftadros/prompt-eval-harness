---
source_slug: llm-json-in-php
source_url: https://anthonytadros.me/writing/llm-json-in-php/
heading: 'Send the schema'
excerpted: 2026-08-17
tampered: false
---

# Getting reliable JSON out of an LLM in PHP
## Send the schema

When the provider lets you attach a JSON schema to the request, attach it. It raises the odds the response parses on the first try, and it costs almost nothing: the schema goes in the response-format field of the same call you were already making with Guzzle, and you turn on strict mode if there is one. It does most of the work. Just not all of it.

Then decode like the schema might not have held. Even with one attached, a model under load or sitting behind a slightly older endpoint can wrap the object in a sentence or a markdown fence, and a naive json_decode throws on the spot. I pull the JSON out of whatever surrounds it and decode with errors promoted to exceptions, so a malformed response becomes a caught, retryable condition instead of a fatal halfway down a controller.

```
function decodeJson(string $raw): array
{
    // models sometimes wrap JSON in prose or a ```json fence
    if (preg_match('/\{.*\}/s', $raw, $m)) {
        $raw = $m[0];
    }
    return json_decode($raw, true, flags: JSON_THROW_ON_ERROR);
}
```
