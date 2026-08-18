---
id: rag-over-internal-docs
url: https://anthonytadros.me/writing/rag-over-internal-docs/
date: 2026-06-18
title: 'RAG over a decade of internal docs'
---

# RAG over a decade of internal docs

Vector search over a clean corpus is close to solved, and it demos well. Chunking, index freshness, citations, and an honest refusal decide whether anyone trusts the assistant.

I build the admin and configuration side of an AI knowledge assistant, an LLM product that answers questions over enterprise and campus documentation, with document retrieval, indexing, streaming responses, and guardrails underneath. The pitch is easy to draw on a whiteboard: embed the docs, put the vectors in a store, and hand the top matches for a question to the model. That diagram is real, and it's the piece I worry about least.

Vector search over a clean corpus is close to a solved problem now. Pick a reasonable embedding model, pick a store, tune how many results you pull, and the answers will look good in a demo. That's maybe 80% of the system. The other 20% is where my time goes: cutting documents up so retrieval can find them, keeping the index current while the docs change underneath it, citing sources a person can check, and getting the model to say it doesn't know instead of producing a confident wrong answer. Those four decide whether anyone trusts it.

## Chunking decides what retrieval can find

Retrieval can only return what your chunking made findable. Split a procedure in the middle of step 4 and no embedding model recovers the missing context. Fixed windows of N tokens with some overlap, the version every tutorial shows, hold up until the corpus stops being uniform. A decade of internal documentation is not uniform. It's policy PDFs with deep heading structure, wiki pages people have edited for years, tables of room codes and building hours, onboarding guides, and the occasional scanned memo somebody OCR'd badly in 2017.

Fixed windows treat all of that the same. A 512-token window will happily glue the end of one policy onto the start of an unrelated one and embed the seam as if it were a single thought. When that chunk wins retrieval, the model gets a Frankenstein passage and reasons over a boundary that doesn't exist. So I chunk along the document's own structure first, splitting on headings and keeping list items with their parent; tables stay with their captions. The token limit is still there, but as a fallback for when a single section is genuinely too long.

Two details are worth the extra code. Carry a little parent context into each chunk, the document title and the heading path, so a fragment about "renewal" still knows it lives under "Parking Permits." And store enough metadata on every chunk to filter before you rank: source document, section, last-modified date, access scope. Filtering on metadata first and ranking by similarity second is cheaper and more accurate than asking the embedding to encode all of that on its own. The metadata habit is older than any of this for me. I spent years on data remediation work, and that whole job was knowing exactly what a piece of data was and where it lived.

## Freshness is an indexing problem

A demo runs on a frozen corpus, and real documentation moves. A building changes its hours. A policy picks up a new clause, and a deprecated procedure needs to stop showing up at all. If the index is a one-time batch job, each of those edits rots an answer somewhere, and nobody notices until a user acts on stale guidance. This is the piece of RAG that looks most like ordinary systems engineering, which I suspect is why teams that came in through the model side neglect it.

The shape that's held up for me is a pipeline keyed on a content hash per source document, never a script somebody reruns by hand. When a document changes, re-chunk and re-embed just that document, and delete the old version's vectors in the same operation that writes the new ones. The deletes matter as much as the writes. The classic production failure is the orphaned chunk, a fragment of a document that was removed or rewritten months ago, still sitting in the index and winning retrieval for some unlucky query. A pipeline that only ever adds keeps every one of those forever.

- Key every chunk to a source document id and a content hash, so a re-index only touches what changed.
- When a document changes, delete its old vectors in the same transaction that writes the new ones; retrieval should never straddle two versions.
- Stamp each chunk with a last-indexed timestamp and surface it, so "when did the assistant last see this?" has a real answer.
- Run a reconciliation job that removes chunks whose source document no longer exists. They creep in even when the pipeline behaves.

It's the same discipline as any integration job that has to stay correct while the data underneath keeps moving, which is most of what I've done for the last ten years. The payoff is that when someone says the assistant is out of date, there's a number to check.

## Citations, end to end

If the assistant says the library closes at 9pm, the user needs to see which document said that and be able to follow the link. A person who gets burned once by an answer they couldn't check will usually stop using the tool, and they won't tell you. Citing well also reaches back through the whole build, because the thread from answer to source has to survive every stage in between.

So the chunk carries its source identity from the moment it's created, retrieval returns that identity alongside the text, and the prompt directs the model to attribute each claim to a specific passage it was handed. That last step gets checked on the way out. If the model cites a source that wasn't in the retrieved set, that's a failure, and I strip or flag it before anyone sees it. A citation that doesn't resolve to a real, retrieved document is worse than no citation, because it manufactures confidence the system didn't earn.

Tying answers to sources also makes evaluation concrete. "Does the cited passage support the claim" is a sharper test than a human skimming an answer for whether it seems right. And bad citations are often the first visible symptom of bad retrieval or bad chunking upstream, so they double as a diagnostic for the whole pipeline.

## The honest "I don't know"

The most important behavior, and the hardest to get, is refusal: when the documentation doesn't cover a question, the assistant has to say so. The default behavior of these models is the opposite. Hand a capable model a vague question and some loosely related passages and it will produce a fluent, plausible answer that's wrong, because fluent and plausible is what it was trained to be. Over real policies that failure does damage, since the wrong answer sounds exactly as confident as a correct one.

Prompt wording alone won't hold that line, so I build refusal in layers. The first layer runs before the model does: if the top retrieval results come back weak or thin, that's a signal to refuse or to narrow the question, and pushing ahead on hope is where the confident wrong answers come from. The prompt itself gives the model explicit permission to say the documents don't cover this, worded so refusing is a normal outcome and nothing discourages it. And once the model has answered, a final check confirms the answer is grounded in the retrieved passages instead of free-floating assertion. Layered checks beat any single clever instruction, the same way one firewall rule doesn't make a system secure.

Refusal is also a tradeoff to own out loud. Tune it too eager and the assistant hallucinates; too cautious and it shrugs at questions it could have answered, which trains people to stop asking. It's a precision/recall dial on trust, and it belongs wherever a wrong answer costs more than a missed one. For documentation people use to make decisions, I lean toward refusing when unsure. "I couldn't find that in the docs" costs someone a trip to a human. A confident wrong answer gets acted on, and the person finds out later.

## What I'd tell someone starting

Stand up basic retrieval in an afternoon and resist polishing it, because it will already look good. The real time goes to the other 20%, the four things above, and to instrumenting them, so retrieval quality, index freshness, and citation validity show up as numbers. When one of them slips, the metrics tell you. The alternative is finding out from a user who acted on a stale answer.
