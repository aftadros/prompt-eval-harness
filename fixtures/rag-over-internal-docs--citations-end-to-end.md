---
source_slug: rag-over-internal-docs
source_url: https://anthonytadros.me/writing/rag-over-internal-docs/
heading: 'Citations, end to end'
excerpted: 2026-08-17
tampered: false
---

# RAG over a decade of internal docs
## Citations, end to end

If the assistant says the library closes at 9pm, the user needs to see which document said that and be able to follow the link. A person who gets burned once by an answer they couldn't check will usually stop using the tool, and they won't tell you. Citing well also reaches back through the whole build, because the thread from answer to source has to survive every stage in between.

So the chunk carries its source identity from the moment it's created, retrieval returns that identity alongside the text, and the prompt directs the model to attribute each claim to a specific passage it was handed. That last step gets checked on the way out. If the model cites a source that wasn't in the retrieved set, that's a failure, and I strip or flag it before anyone sees it. A citation that doesn't resolve to a real, retrieved document is worse than no citation, because it manufactures confidence the system didn't earn.

Tying answers to sources also makes evaluation concrete. "Does the cited passage support the claim" is a sharper test than a human skimming an answer for whether it seems right. And bad citations are often the first visible symptom of bad retrieval or bad chunking upstream, so they double as a diagnostic for the whole pipeline.
