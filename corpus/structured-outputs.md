---
id: structured-outputs
url: https://anthonytadros.me/writing/structured-outputs/
date: 2026-06-07
title: 'Structured outputs deleted half my parsing code'
---

# Structured outputs deleted half my parsing code

For three years I maintained the layer that turned model text into something PHP could act on. Provider-enforced schemas deleted most of that code, though not the validation that mattered.

For about three years I owned the parsing layer between a language model and a PHP service. The model sat behind the admin and configuration surface of an AI knowledge assistant, and its job was to hand back structured answers: a category, a confidence band, a short list of suggested document tags, sometimes a small object describing a config change a user had asked for in plain English. The model returned text. My code turned that text into something the service could act on, and that code was a swamp.

I've been writing integration glue since 2016, and before that I was migrating legacy desktop database forms into Oracle and building enterprise ETL job sequences, where every field had a type and a length and a NOT NULL constraint. I knew what a contract was supposed to feel like. The LLM had nothing of the sort. Its contract was a line at the end of the prompt that said "respond in JSON."

## The parsing layer

You ask for JSON and most of the time you get JSON. The exceptions were my job. Responses came back wrapped in markdown code fences, so I stripped fences. Then the model took to prefixing the JSON with "Here is the structured output you requested," and I was finding the first opening brace and slicing. A trailing comma broke the decoder; a regex killed trailing commas before parsing. Confidence was supposed to be a number between 0 and 1 until it came back as the string "high", and I wrote a normalizer. Later it was 0.85 on one call and "85%" on the next. I wrote another.

Every one of those was a real bug, with a ticket and a customer-facing symptom behind it. None of them were hard. They were the same bug in different clothes, and the function that dealt with them grew to a few hundred lines of PHP, most of it defensive: try to decode, catch, repair, decode again, and when the JSON was unsalvageable, fall back to a regex that pulled fields out of prose. Somewhere in the middle of that function was a comment I wrote that just said `// model sometimes does this on Mondays`. It wasn't actually Mondays. I never found the pattern, and that was the problem. There wasn't one I could pin down, only a long tail of formatting accidents I patched one at a time.

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

## What got deleted

When I moved the first endpoint over, the diff took out a good chunk of the handling code around that call:

- The fence-stripping and brace-finding cleanup. The output is raw conformant JSON now.
- The type-coercion layer that turned strings into numbers and back, since types are declared and enforced upstream.
- Enum normalization for categories.
- The regex fallback that scraped fields out of prose when the JSON wouldn't parse. Structural failures stopped happening, so it had nothing left to catch.
- A chunk of the unit tests around the handler, which existed to pin down formatting edge cases that can no longer occur.

"Gone" doesn't mean I deleted tests on faith. The failure modes they guarded became unreachable by construction, the same way you stop writing a null check after the column goes NOT NULL in the database.

## What it didn't fix

Structured outputs guarantee shape and nothing else. The model will hand you a perfectly typed `confidence` of 0.95 on an answer that's wrong. It will pick the enum value `access` when the right answer was `billing`, in flawless JSON. The schema is a type system, and type systems have never told you your logic is correct, only that the data fits the slots.

The validation work changed character. I stopped checking whether the response parses and started checking whether it's sane. Does this category make sense given the input? Is this tag one we support, or did the model invent a plausible-looking string that passed the schema because the schema only said "string"? That last one bit me. A free-form string field in a schema is still free-form, and if you want the tag to be a real tag, you constrain it with an enum or you check it against your own list after the fact.

There are sharper edges too. Deeply nested schemas, long enums, and some combinations of optional fields can degrade answer quality, because you're constraining the model's generation path and sometimes the path it wanted was outside your grammar. Tighter isn't automatically better. I've watched a model give a worse answer under a rigid schema than it gave in free text, then get it right again once I flattened the structure.

## Retry on schema mismatch

You still need a retry path, just a much smaller one. With strict provider-side constraint, structural mismatch is rare, but it isn't zero across every model and setting, and schema-valid-but-wrong is real. My retry logic has two tiers now. The first is the old reflex: if the response somehow fails to validate against the schema, retry once. In practice this almost never fires anymore, which is the point.

The second tier is the one I had to think about. Once the response validates, it runs through a semantic check that lives in my code, not the model's: is the tag in my supported set, is the confidence consistent with the category I'd expect for this kind of input. When that check fails, I retry with the failure fed back into the prompt: you returned tag X, which is not a valid tag, choose from this list. That's a content retry, and it stays mine, because the provider can enforce the format but has no idea what "valid" means for this product.

## Where the job went

What struck me once the parsing code was gone is that I'd been doing the model's type-checking by hand for most of my career, under other names. A reporting tool pointed at a database that lied to it, ETL jobs hardened against upstream files that changed format without warning. There was scanner output I parsed just to feed a remediation step. Every integration I've built had a layer whose only job was making a sloppy upstream conform to a contract the downstream needed.

Structured outputs moved that layer to the boundary of the call, where it belongs: declared once in the request, enforced by the provider. What's left on my side is deciding what a correct answer looks like and checking for it. I wrote the parsing half by hand for a decade, and I don't miss it.
