---
id: llm-cost-at-campus-scale
url: https://anthonytadros.me/writing/llm-cost-at-campus-scale/
date: 2026-06-07
title: 'What an LLM costs at campus scale'
---

# What an LLM costs at campus scale

At campus scale the model's meter becomes part of the architecture. Most of what controls the bill is query-tuning habit carried over from my Oracle days, applied to prompts and tokens instead of SQL.

I build the admin and configuration side of an AI knowledge assistant, an LLM product that retrieves documents, indexes them, streams answers, and runs guardrails on top. The model underneath is a metered dependency. Every answer has a price in tokens and a price in seconds, and with a few hundred curious users you don't notice either one. At campus scale the meter is part of the architecture.

I spent years before this writing SQL against Oracle and Crystal Reports, tuning queries that scanned tables nobody had indexed in a decade. That work is still how I read a model call. A prompt is a query, the context window is a scan, and the levers here are the same ones you reach for when a report takes 40 seconds and the business wants 4. The questions are the same, too: where does the work happen, and what's getting read twice or read for no reason.

## Tokens are the row count

You pay per token, with input and output priced separately. Input is cheap and plentiful; output costs several times more and arrives one token at a time. A retrieval-augmented answer is input-heavy by design, because you stuff the prompt with retrieved passages, system instructions, formatting rules, maybe a few examples, and ask for a short answer back. It's easy to end up with a big prompt producing a small reply, which means almost all the spend is on the read, not the write.

That ratio is a full table scan returning one row, and the fix is the same fix: read less. Tighten retrieval so the top few passages go in instead of a long list. The system prompt gets the same audit, since it grows by accretion, every edge case earning its own paragraph, and few-shot examples can come out once the model behaves without them. It's accounting. Multiplied by daily volume, it's what moves a per-request cost from real money to a rounding error.

I don't track 'average latency' as one number. For each request I record input tokens, output tokens, and wall-clock time, then attach a dollar figure at the current per-token rates, and it's that per-request cost, bucketed by feature, that tells you whether a change helped. The monthly bill can't. It averages everything together and hides the offender.

## Caching the stable prefix

The lever with the best return for the least work is prompt caching. Most providers will cache a stable prefix of your prompt and charge a fraction of the normal input price to reuse it. In a retrieval assistant a big chunk of every prompt is identical from call to call anyway, the system instructions and the formatting rules and the guardrail preamble, with only the user's question and the retrieved passages changing between requests.

So order the prompt deliberately, stable material first, volatile last: static system prompt, then tool definitions, then retrieved context, then the question. The cached prefix can cover everything up to the first point where content varies. Get the ordering right and a high-traffic endpoint's long, repeated preamble bills at the cache rate instead of full freight, which is a real cut to effective input cost.

This is the LLM version of building an index. The query was always going to run; you're just paying to not re-read the same bytes every time. The discipline is one I recognize from databases, which is to keep the stable parts stable. The moment someone injects a timestamp or a per-user token near the top of the prompt, the cacheable prefix shrinks to nothing and the savings evaporate. Cache invalidation by accident is a real bug, and it shows up as a cost regression instead of a crash, so you only catch it if you're watching per-request cost.

## Work that can wait

Not every call has a person waiting on the other end. A surprising amount of what a knowledge assistant does happens offline: indexing new documents, generating summaries, extracting metadata, pre-computing embeddings, running quality checks over a corpus. Nobody is staring at a spinner for any of it, so the only thing worth optimizing there is price.

Providers price the difference for you. Batch processing for asynchronous jobs typically runs at a steep discount against the real-time rate, in exchange for slower, best-effort turnaround. My rule is that if nobody is blocked on the result, it goes through the batch path. This is the same instinct as moving a heavy report off the transactional database onto a nightly job, which is most of what I was doing when I built an Access-to-Oracle migration years ago. Reindexing a department's document set overnight should never be billed at interactive prices.

## Streaming and retries

Streaming doesn't make the model cheaper or the generation faster. You pay for the same output tokens and the model spends the same time producing them. What changes is when the user sees the first word: time-to-first-token drops to a fraction of a second, and a long answer stops feeling frozen.

That matters because perceived latency is what drives retries. Somebody waits eight seconds on a blank screen, hits the button again, and now you've paid for two generations to answer one question. Streaming kills that failure mode, so I count it as a cost control even though it touches no token price directly. It also changes the timeout math: an answer that's slow but visibly making progress can keep its connection open, instead of getting failed and turning into a retry you also pay for.

## Which model gets the question

The biggest structural lever is admitting that not every question deserves your best model. Providers sell a tiered lineup. The small fast model costs a little, the big capable one costs a lot, and there's usually something in between; the per-token gap between the cheap tier and the flagship is often an order of magnitude. Send everything to the flagship and you're paying premium rates to answer 'what are the library hours,' which the small model handles perfectly.

Routing is where the query-planner metaphor pays off most directly. A planner picks an access path from the shape of the query, and you can do the same thing: classify the request, then route it. Short factual lookups with a clean retrieval hit go to the cheap model; ambiguous, multi-step, synthesis-heavy questions go to the smart one. The classifier itself can be the small model, or even a rules check on retrieval confidence, so the routing decision costs close to nothing.

- Cheap tier: direct factual answers grounded in one high-confidence passage, where the model is mostly reformatting retrieved text.
- Smart tier: questions that span multiple documents, have to reason over conflicting sources, or came back from retrieval weak enough that the model has real work to do.
- Escalation: start cheap, and if a confidence check or guardrail flags the answer as thin, retry once on the smart model instead of defaulting everything upward.

Escalation is the one I trust most, because it fails toward quality. You don't have to predict which questions are hard. Answer cheaply, check the result, and pay for the expensive model only on the cases that earn it. Done well, most traffic settles on the cheap tier and the average cost per request drops, while the answers people scrutinize still get the strong model.

## Guardrails have a cost too

Every safety layer you bolt on is another model call or another pass of tokens, and those add up the same way everything else here does. A moderation check before the answer, a groundedness check after it, a second model verifying the first: each is defensible on its own, and together they can double your per-request cost without anyone deciding to double it. My background is in security, remediating PII across university machines with tooling like Splunk and Identity Finder, so I'm not going to be the one arguing guardrails away. I just want each check to carry a known price. Decide which ones run on every request and which run on a sample, and don't spend a heavy verification pass protecting a short answer unless the risk warrants it.

## Instrumentation

All of it collapses without measurement. The single most useful thing I did was make cost per request a first-class metric next to latency and error rate. Every call records the model used, input tokens, cached tokens, output tokens, and the path it took (cheap, smart, escalated, or batch). Multiply by the live rates and you get a dollar figure you can slice by feature, endpoint, or tenant.

Once that number exists, the optimizations stop being guesses. It will show you the configuration screen generating a bloated prompt because someone pasted an entire instruction manual into the system message, or the endpoint whose cache hit rate fell to zero after a refactor moved a variable to the top of the prompt, or the tenant whose traffic is all flagship-tier when half of it should route cheap. It's the slow query log for model calls.

> A prompt is a query and the context window is a scan. The bill is the cost estimate, except you get it after the query has run.

So the toolkit: cache the repeated prefix, batch what can wait, stream so people don't retry, route cheap before smart, and keep a price on the guardrails. Most of it I'd already learned against Oracle, where the cost of a careless read was somebody waiting 40 seconds for a report. Here the cost is dollars, multiplied by a campus.
