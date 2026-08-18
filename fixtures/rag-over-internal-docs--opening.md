---
source_slug: rag-over-internal-docs
source_url: https://anthonytadros.me/writing/rag-over-internal-docs/
heading: 'Opening'
excerpted: 2026-08-17
tampered: false
---

# RAG over a decade of internal docs
## Opening

I build the admin and configuration side of an AI knowledge assistant, an LLM product that answers questions over enterprise and campus documentation, with document retrieval, indexing, streaming responses, and guardrails underneath. The pitch is easy to draw on a whiteboard: embed the docs, put the vectors in a store, and hand the top matches for a question to the model. That diagram is real, and it's the piece I worry about least.

Vector search over a clean corpus is close to a solved problem now. Pick a reasonable embedding model, pick a store, tune how many results you pull, and the answers will look good in a demo. That's maybe 80% of the system. The other 20% is where my time goes: cutting documents up so retrieval can find them, keeping the index current while the docs change underneath it, citing sources a person can check, and getting the model to say it doesn't know instead of producing a confident wrong answer. Those four decide whether anyone trusts it.
