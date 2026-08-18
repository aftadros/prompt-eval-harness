---
id: llm-json-in-php
url: https://anthonytadros.me/writing/llm-json-in-php/
date: 2026-07-26
title: 'Getting reliable JSON out of an LLM in PHP'
---

# Getting reliable JSON out of an LLM in PHP

The structured-output demos are all Python, but underneath them is a plain HTTP call. This is the small amount of PHP that turns a model response into something the rest of the code can act on.

Structured outputs get sold as the end of parsing: you ask for JSON and JSON is what comes back. On a PHP stack that takes some assembly, because the convenience methods everyone demos live in the Python SDK, and underneath them it's the same raw HTTP call you're already making. There's a better reason to build the net yourself, though. Schema-valid and correct are not the same claim. A model can hand you a perfectly shaped object full of wrong values, and the shape is all the API guarantees.

A lot of my time goes to pulling structured data out of unstructured internal documents, which means the model's output becomes a record the rest of my code acts on. So I treat the response the way a security background trains you to treat anything off the wire: the shape might be wrong and the values might be wrong, and neither gets any further until it's been checked.

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

## One repair attempt

When the parse or the validation fails, the model gets one more try with the failure attached, because often it just needs to be told what it got wrong. Feed back the specific error and ask again. If the second answer is still bad, fall back to whatever the feature does without the extraction rather than keep hammering the endpoint. A model that missed twice on the same input isn't going to be argued into it on the fifth attempt, and you're paying full price for every one of them.

None of this is much code. The schema mode does the heavy lifting, and everything after it is insurance for the times it slips, which on a busy endpoint is more often than the marketing implies. What the extra lines buy is the thing the demos pretend you already have: a response your PHP code can act on, with no layer of array_key_exists and silent shrugs holding it up.
