---
source_slug: llm-cost-at-campus-scale
source_url: https://anthonytadros.me/writing/llm-cost-at-campus-scale/
heading: 'Work that can wait'
excerpted: 2026-08-17
tampered: false
---

# What an LLM costs at campus scale
## Work that can wait

Not every call has a person waiting on the other end. A surprising amount of what a knowledge assistant does happens offline: indexing new documents, generating summaries, extracting metadata, pre-computing embeddings, running quality checks over a corpus. Nobody is staring at a spinner for any of it, so the only thing worth optimizing there is price.

Providers price the difference for you. Batch processing for asynchronous jobs typically runs at a steep discount against the real-time rate, in exchange for slower, best-effort turnaround. My rule is that if nobody is blocked on the result, it goes through the batch path. This is the same instinct as moving a heavy report off the transactional database onto a nightly job, which is most of what I was doing when I built an Access-to-Oracle migration years ago. Reindexing a department's document set overnight should never be billed at interactive prices.
