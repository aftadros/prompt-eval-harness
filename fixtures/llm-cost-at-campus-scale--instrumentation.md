---
source_slug: llm-cost-at-campus-scale
source_url: https://anthonytadros.me/writing/llm-cost-at-campus-scale/
heading: 'Instrumentation'
excerpted: 2026-08-17
tampered: false
---

# What an LLM costs at campus scale
## Instrumentation

All of it collapses without measurement. The single most useful thing I did was make cost per request a first-class metric next to latency and error rate. Every call records the model used, input tokens, cached tokens, output tokens, and the path it took (cheap, smart, escalated, or batch). Multiply by the live rates and you get a dollar figure you can slice by feature, endpoint, or tenant.

Once that number exists, the optimizations stop being guesses. It will show you the configuration screen generating a bloated prompt because someone pasted an entire instruction manual into the system message, or the endpoint whose cache hit rate fell to zero after a refactor moved a variable to the top of the prompt, or the tenant whose traffic is all flagship-tier when half of it should route cheap. It's the slow query log for model calls.

> A prompt is a query and the context window is a scan. The bill is the cost estimate, except you get it after the query has run.

So the toolkit: cache the repeated prefix, batch what can wait, stream so people don't retry, route cheap before smart, and keep a price on the guardrails. Most of it I'd already learned against Oracle, where the cost of a careless read was somebody waiting 40 seconds for a report. Here the cost is dollars, multiplied by a campus.
