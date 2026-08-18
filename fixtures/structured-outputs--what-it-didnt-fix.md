---
source_slug: structured-outputs
source_url: https://anthonytadros.me/writing/structured-outputs/
heading: "What it didn't fix"
excerpted: 2026-08-17
tampered: false
---

# Structured outputs deleted half my parsing code
## What it didn't fix

Structured outputs guarantee shape and nothing else. The model will hand you a perfectly typed `confidence` of 0.95 on an answer that's wrong. It will pick the enum value `access` when the right answer was `billing`, in flawless JSON. The schema is a type system, and type systems have never told you your logic is correct, only that the data fits the slots.

The validation work changed character. I stopped checking whether the response parses and started checking whether it's sane. Does this category make sense given the input? Is this tag one we support, or did the model invent a plausible-looking string that passed the schema because the schema only said "string"? That last one bit me. A free-form string field in a schema is still free-form, and if you want the tag to be a real tag, you constrain it with an enum or you check it against your own list after the fact.

There are sharper edges too. Deeply nested schemas, long enums, and some combinations of optional fields can degrade answer quality, because you're constraining the model's generation path and sometimes the path it wanted was outside your grammar. Tighter isn't automatically better. I've watched a model give a worse answer under a rigid schema than it gave in free text, then get it right again once I flattened the structure.
