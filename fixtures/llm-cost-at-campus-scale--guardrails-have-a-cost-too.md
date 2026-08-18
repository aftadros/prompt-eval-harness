---
source_slug: llm-cost-at-campus-scale
source_url: https://anthonytadros.me/writing/llm-cost-at-campus-scale/
heading: 'Guardrails have a cost too'
excerpted: 2026-08-17
tampered: false
---

# What an LLM costs at campus scale
## Guardrails have a cost too

Every safety layer you bolt on is another model call or another pass of tokens, and those add up the same way everything else here does. A moderation check before the answer, a groundedness check after it, a second model verifying the first: each is defensible on its own, and together they can double your per-request cost without anyone deciding to double it. My background is in security, remediating PII across university machines with tooling like Splunk and Identity Finder, so I'm not going to be the one arguing guardrails away. I just want each check to carry a known price. Decide which ones run on every request and which run on a sample, and don't spend a heavy verification pass protecting a short answer unless the risk warrants it.
