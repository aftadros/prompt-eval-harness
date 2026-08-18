---
source_slug: rag-over-internal-docs
source_url: https://anthonytadros.me/writing/rag-over-internal-docs/
heading: 'Chunking decides what retrieval can find'
excerpted: 2026-08-17
tampered: false
---

# RAG over a decade of internal docs
## Chunking decides what retrieval can find

Retrieval can only return what your chunking made findable. Split a procedure in the middle of step 4 and no embedding model recovers the missing context. Fixed windows of N tokens with some overlap, the version every tutorial shows, hold up until the corpus stops being uniform. A decade of internal documentation is not uniform. It's policy PDFs with deep heading structure, wiki pages people have edited for years, tables of room codes and building hours, onboarding guides, and the occasional scanned memo somebody OCR'd badly in 2017.

Fixed windows treat all of that the same. A 512-token window will happily glue the end of one policy onto the start of an unrelated one and embed the seam as if it were a single thought. When that chunk wins retrieval, the model gets a Frankenstein passage and reasons over a boundary that doesn't exist. So I chunk along the document's own structure first, splitting on headings and keeping list items with their parent; tables stay with their captions. The token limit is still there, but as a fallback for when a single section is genuinely too long.

Two details are worth the extra code. Carry a little parent context into each chunk, the document title and the heading path, so a fragment about "renewal" still knows it lives under "Parking Permits." And store enough metadata on every chunk to filter before you rank: source document, section, last-modified date, access scope. Filtering on metadata first and ranking by similarity second is cheaper and more accurate than asking the embedding to encode all of that on its own. The metadata habit is older than any of this for me. I spent years on data remediation work, and that whole job was knowing exactly what a piece of data was and where it lived.
