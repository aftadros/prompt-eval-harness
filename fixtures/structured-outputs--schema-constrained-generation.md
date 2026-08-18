---
source_slug: structured-outputs
source_url: https://anthonytadros.me/writing/structured-outputs/
heading: 'Schema-constrained generation'
excerpted: 2026-08-17
tampered: false
---

# Structured outputs deleted half my parsing code
## Schema-constrained generation

Structured outputs move the contract from your parser into the request. Instead of asking nicely and cleaning up afterward, you send a JSON Schema as part of the call, and the provider constrains generation so the tokens the model emits have to conform to it. Under a true constrained decoder, a trailing comma or a stray "Here is your answer" preamble can't happen, because those tokens aren't valid continuations of anything the schema allows. There's no extra instruction-following involved. The decoder is restricted to a grammar derived from your schema, invalid tokens are masked out before sampling, and the guarantee is structural: you get back a string that parses, with the fields and types you declared. Say `confidence` is a number with minimum 0 and maximum 1, and a number in that range is what shows up.

```
$schema = [
  'type' => 'object',
  'properties' => [
    'category'   => ['type' => 'string', 'enum' => ['billing','access','content','other']],
    'confidence' => ['type' => 'number', 'minimum' => 0, 'maximum' => 1],
    'tags'       => ['type' => 'array', 'items' => ['type' => 'string'], 'maxItems' => 5],
  ],
  'required' => ['category', 'confidence'],
  'additionalProperties' => false,
];
```

The enum deleted the most code. Free-text classification meant the model could and did return "Billing", "billing", "billing issue", "BILLING", and once, memorably, "this looks like a billing question to me." I had a lowercase-and-fuzzy-match step to collapse all of that into one of four buckets. With the enum in the schema there are four buckets and the model picks one. The mapping step is gone, and so is the test file that covered it.
