---
source_slug: structured-outputs
source_url: https://anthonytadros.me/writing/structured-outputs/
heading: 'Where the job went'
excerpted: 2026-08-17
tampered: false
---

# Structured outputs deleted half my parsing code
## Where the job went

What struck me once the parsing code was gone is that I'd been doing the model's type-checking by hand for most of my career, under other names. A reporting tool pointed at a database that lied to it, ETL jobs hardened against upstream files that changed format without warning. There was scanner output I parsed just to feed a remediation step. Every integration I've built had a layer whose only job was making a sloppy upstream conform to a contract the downstream needed.

Structured outputs moved that layer to the boundary of the call, where it belongs: declared once in the request, enforced by the provider. What's left on my side is deciding what a correct answer looks like and checking for it. I wrote the parsing half by hand for a decade, and I don't miss it.
