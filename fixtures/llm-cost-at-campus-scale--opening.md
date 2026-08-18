---
source_slug: llm-cost-at-campus-scale
source_url: https://anthonytadros.me/writing/llm-cost-at-campus-scale/
heading: 'Opening'
excerpted: 2026-08-17
tampered: false
---

# What an LLM costs at campus scale
## Opening

I build the admin and configuration side of an AI knowledge assistant, an LLM product that retrieves documents, indexes them, streams answers, and runs guardrails on top. The model underneath is a metered dependency. Every answer has a price in tokens and a price in seconds, and with a few hundred curious users you don't notice either one. At campus scale the meter is part of the architecture.

I spent years before this writing SQL against Oracle and Crystal Reports, tuning queries that scanned tables nobody had indexed in a decade. That work is still how I read a model call. A prompt is a query, the context window is a scan, and the levers here are the same ones you reach for when a report takes 40 seconds and the business wants 4. The questions are the same, too: where does the work happen, and what's getting read twice or read for no reason.
