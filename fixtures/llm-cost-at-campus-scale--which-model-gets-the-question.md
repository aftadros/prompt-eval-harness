---
source_slug: llm-cost-at-campus-scale
source_url: https://anthonytadros.me/writing/llm-cost-at-campus-scale/
heading: 'Which model gets the question'
excerpted: 2026-08-17
tampered: false
---

# What an LLM costs at campus scale
## Which model gets the question

The biggest structural lever is admitting that not every question deserves your best model. Providers sell a tiered lineup. The small fast model costs a little, the big capable one costs a lot, and there's usually something in between; the per-token gap between the cheap tier and the flagship is often an order of magnitude. Send everything to the flagship and you're paying premium rates to answer 'what are the library hours,' which the small model handles perfectly.

Routing is where the query-planner metaphor pays off most directly. A planner picks an access path from the shape of the query, and you can do the same thing: classify the request, then route it. Short factual lookups with a clean retrieval hit go to the cheap model; ambiguous, multi-step, synthesis-heavy questions go to the smart one. The classifier itself can be the small model, or even a rules check on retrieval confidence, so the routing decision costs close to nothing.

- Cheap tier: direct factual answers grounded in one high-confidence passage, where the model is mostly reformatting retrieved text.
- Smart tier: questions that span multiple documents, have to reason over conflicting sources, or came back from retrieval weak enough that the model has real work to do.
- Escalation: start cheap, and if a confidence check or guardrail flags the answer as thin, retry once on the smart model instead of defaulting everything upward.

Escalation is the one I trust most, because it fails toward quality. You don't have to predict which questions are hard. Answer cheaply, check the result, and pay for the expensive model only on the cases that earn it. Done well, most traffic settles on the cheap tier and the average cost per request drops, while the answers people scrutinize still get the strong model.
