---
source_slug: llm-cost-per-request
source_url: https://anthonytadros.me/writing/llm-cost-per-request/
heading: 'Why the unit is the request'
excerpted: 2026-08-17
tampered: false
---

# Putting a dollar figure on every model call
## Why the unit is the request

I track the per-call number rather than the monthly total because the per-call number can be acted on the same day. A change either moved it or it didn't, and you see which one immediately instead of waiting weeks for an invoice that arrives with everything averaged together. It also survives growth. Traffic doubling roughly doubles the bill and tells you nothing; cost per request drifting up while traffic is flat says some specific feature got more expensive, and points you at it.

Once the per-request cost exists, the slicing falls out of labels the request already carries. Group it by feature and the expensive feature names itself. The same field grouped by endpoint surfaces the one screen building a bloated prompt, and grouped by tenant it surfaces the customer whose traffic all goes to the flagship when half of it could ride the cheap model.
