---
source_slug: llm-json-in-php
source_url: https://anthonytadros.me/writing/llm-json-in-php/
heading: 'Opening'
excerpted: 2026-08-17
tampered: false
---

# Getting reliable JSON out of an LLM in PHP
## Opening

Structured outputs get sold as the end of parsing: you ask for JSON and JSON is what comes back. On a PHP stack that takes some assembly, because the convenience methods everyone demos live in the Python SDK, and underneath them it's the same raw HTTP call you're already making. There's a better reason to build the net yourself, though. Schema-valid and correct are not the same claim. A model can hand you a perfectly shaped object full of wrong values, and the shape is all the API guarantees.

A lot of my time goes to pulling structured data out of unstructured internal documents, which means the model's output becomes a record the rest of my code acts on. So I treat the response the way a security background trains you to treat anything off the wire: the shape might be wrong and the values might be wrong, and neither gets any further until it's been checked.
