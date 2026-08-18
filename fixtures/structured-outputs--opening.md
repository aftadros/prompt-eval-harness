---
source_slug: structured-outputs
source_url: https://anthonytadros.me/writing/structured-outputs/
heading: 'Opening'
excerpted: 2026-08-17
tampered: false
---

# Structured outputs deleted half my parsing code
## Opening

For about three years I owned the parsing layer between a language model and a PHP service. The model sat behind the admin and configuration surface of an AI knowledge assistant, and its job was to hand back structured answers: a category, a confidence band, a short list of suggested document tags, sometimes a small object describing a config change a user had asked for in plain English. The model returned text. My code turned that text into something the service could act on, and that code was a swamp.

I've been writing integration glue since 2016, and before that I was migrating legacy desktop database forms into Oracle and building enterprise ETL job sequences, where every field had a type and a length and a NOT NULL constraint. I knew what a contract was supposed to feel like. The LLM had nothing of the sort. Its contract was a line at the end of the prompt that said "respond in JSON."
