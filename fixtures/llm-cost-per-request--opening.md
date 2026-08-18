---
source_slug: llm-cost-per-request
source_url: https://anthonytadros.me/writing/llm-cost-per-request/
heading: 'Opening'
excerpted: 2026-08-17
tampered: false
---

# Putting a dollar figure on every model call
## Opening

The invoice at the end of the month is one number, and it's close to useless. It tells you what you spent and nothing about where it went; you can't see which feature is expensive, which tenant is heavy, or whether last week's prompt change cost money or saved it. So I price every model call at the moment it happens and store the result on the request, in the same place I keep latency and error rate.

I've written elsewhere about the levers you pull once you can see the cost. This is about the seeing, which has to come first. The habit comes from years of writing reports against databases, where the bill was paid in wall-clock seconds instead of dollars. You learn fast that "the database is slow" isn't a finding. The finding is which query, run how often, scanning what. A model is the same shape of metered dependency, and "the AI is expensive" is the same non-finding. Attribute the spend to the thing that spent it, or you're staring at a total and guessing.
