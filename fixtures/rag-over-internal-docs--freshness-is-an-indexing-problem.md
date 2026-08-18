---
source_slug: rag-over-internal-docs
source_url: https://anthonytadros.me/writing/rag-over-internal-docs/
heading: 'Freshness is an indexing problem'
excerpted: 2026-08-17
tampered: false
---

# RAG over a decade of internal docs
## Freshness is an indexing problem

A demo runs on a frozen corpus, and real documentation moves. A building changes its hours. A policy picks up a new clause, and a deprecated procedure needs to stop showing up at all. If the index is a one-time batch job, each of those edits rots an answer somewhere, and nobody notices until a user acts on stale guidance. This is the piece of RAG that looks most like ordinary systems engineering, which I suspect is why teams that came in through the model side neglect it.

The shape that's held up for me is a pipeline keyed on a content hash per source document, never a script somebody reruns by hand. When a document changes, re-chunk and re-embed just that document, and delete the old version's vectors in the same operation that writes the new ones. The deletes matter as much as the writes. The classic production failure is the orphaned chunk, a fragment of a document that was removed or rewritten months ago, still sitting in the index and winning retrieval for some unlucky query. A pipeline that only ever adds keeps every one of those forever.

- Key every chunk to a source document id and a content hash, so a re-index only touches what changed.
- When a document changes, delete its old vectors in the same transaction that writes the new ones; retrieval should never straddle two versions.
- Stamp each chunk with a last-indexed timestamp and surface it, so "when did the assistant last see this?" has a real answer.
- Run a reconciliation job that removes chunks whose source document no longer exists. They creep in even when the pipeline behaves.

It's the same discipline as any integration job that has to stay correct while the data underneath keeps moving, which is most of what I've done for the last ten years. The payoff is that when someone says the assistant is out of date, there's a number to check.
