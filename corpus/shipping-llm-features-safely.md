---
id: shipping-llm-features-safely
url: https://anthonytadros.me/writing/shipping-llm-features-safely/
date: 2026-06-30
title: 'Shipping an LLM feature without it going sideways'
---

# Shipping an LLM feature without it going sideways

An LLM endpoint is an expensive, slow, nondeterministic remote dependency, and ten years of integration work taught me how to wrap one of those. The only new failure mode is the successful response you can't use, so output validation gets treated as reliability work.

I've spent ten years wiring together systems that don't trust each other: customer SIS feeds, identity providers, payment endpoints, campus card readers. Integration work teaches you that the happy path is a rounding error. The remote thing will be slow when it matters, will eventually time out or return garbage, and when it goes down it'll be during a demo. A model call is the newest member of that family. An LLM endpoint is a third-party dependency that happens to be unusually slow and expensive, and nondeterministic besides. Every reliability instinct I picked up before I ever touched a token still applies.

These days I build the admin and configuration surface for an AI knowledge assistant, an LLM product that retrieves documents, indexes them, streams answers back, and runs guardrails over the result. The interesting engineering is almost never the prompt. It's the wrapping around the model call, which decides what a bad day at the provider feels like from inside the app.

## A model call is a network call, so treat it like one

The first mistake people make moving from a notebook to production is treating the SDK call like a local function. It's an HTTP request to a busy service, one that can take 30 seconds, return a 5xx, or hang forever. Framed that way, you already own a decade of patterns for it: timeouts, retries, circuit breakers, bulkheads, fallbacks. There's nothing AI-specific in that list. It's the checklist I'd run on any integration to a system I don't control.

What's different is the cost and the shape of failure. When a database read fails, it fails cheap and obvious. A model call can eat 25 seconds and a pile of tokens, then hand back confident nonsense that passes your JSON parse. So the wrapping has to cover outright failure and also the 200 with output you can't use. Reliability and output validation end up being one surface here, and I treat them together.

## Timeouts, and where the number comes from

Every model call gets an explicit timeout, because SDK defaults are usually too generous or missing. The number starts with the user, though. On an interactive HTTP request, a human gives you a few seconds before deciding the thing is broken, and the server has its own ceiling before the connection dies. Work backward from that ceiling and hand the model whatever slice remains after retrieval, guardrails, and serialization take their cut.

Streaming complicates this. A streamed response can run long in total and still be fine, since tokens keep arriving, so I track two clocks: time-to-first-token and total wall time. A long total with bytes flowing is healthy, but five seconds of nothing on the wire is a stall, and I kill it. Watching the inter-token gap lets me tell a long good answer from a dead connection; the total alone can't.

## Retries that don't make the fire bigger

Retries are where good intentions cause outages. The rule I carried over from integration work: retry only what's genuinely transient, and never in a way that piles load onto something already struggling. A 429 or a 5xx means the upstream is saturated, and three immediate retries against a saturated service turns a blip into an outage you caused. Retries here are bounded, usually at two, with exponential backoff and jitter to keep a thousand clients from resynchronizing into a thundering herd the moment the service recovers.

I sort errors into three buckets before deciding anything. Transient failures, the timeouts and 429s and 5xxs and connection resets, get the bounded backoff. Permanent failures fail fast, because retrying a 400 from a malformed request, an auth error, or a context-length overflow just spends the user's time and your money. The nasty one is the middle bucket, the 200 that came back with output you can't use. That isn't a retry candidate by default. It's a validation failure, and it routes to the fallback path, since asking the same question the same way usually gets you the same bad answer.

## The circuit breaker

When the model endpoint is genuinely down, the worst thing a service can do is keep trying, so that every user waits out the full timeout before seeing a failure. That converts a provider outage into a latency disaster across the whole app. A circuit breaker fixes it. Past a threshold of failures in a window, the breaker opens and calls fail immediately for a cool-down period instead of hanging. Every so often it lets one probe request through; if the probe succeeds, it closes and traffic resumes.

The payoff shows during the outage itself. Users get an instant, honest "this isn't available right now" in place of a 25-second spinner that ends in the same place. Fast failure also protects your own thread pools and connection limits from filling with doomed requests, which is the usual mechanism when one slow dependency drags down everything sharing the process. On a PHP and Kubernetes platform, where a stuck worker is a worker that isn't serving anyone else, I don't consider that protection optional.

## What the user sees when the model is down

Every model-backed feature needs an answer to one question: what does the user see when the model is unavailable? "An error" is the lazy answer and usually the wrong one. In a retrieval-augmented assistant, retrieval and generation come apart cleanly. If generation fails, I can often still return the retrieved source documents with their citations, plus a plain note that the summarized answer isn't available right now. The person came looking for information, and the ranked passages are useful on their own. Only the synthesized paragraph on top degraded, and the note says so.

This is where the integration mindset pays off most directly. The product is a stack of capabilities rather than one monolithic call, so failure can be partial. Retrieval up with generation down means showing sources. If it's the guardrail service that's down, I fail closed and ship nothing, since an unchecked answer is worse than no answer. Which way each component fails, open or closed, is a decision I make on purpose, never one I inherit from whatever the library does by default.

## The kill switch

Every LLM feature I ship has a flag that turns it off without a deploy. It's the cheapest insurance in the whole system, and people skip it because nothing is wrong on launch day. The day you need it, you need it within seconds, and no build-and-release cycle moves that fast. That day looks like a bad prompt change shipping, a provider suddenly returning unsafe content, a cost spike from a runaway loop, or a guardrail regression. Whichever it is, the flag drops the feature to its fallback path and you debug calmly, with the harm already stopped.

I keep the switch coarse and boring. One config flag, read on every request, with no cache in front that would delay it by ten minutes. Off means the feature behaves exactly like its graceful-degradation path. The assistant says the summarized answer is unavailable, and retrieval and the rest of the app keep working. The switch isn't an error state; it's a known, tested mode the system enters on purpose, which means I can rehearse it. A kill switch you've never flipped is a guess.

## Log enough to reconstruct the call

Nondeterminism makes LLM bugs miserable, and logging is how you claw back ground. When a user says the assistant gave a strange answer, I need to rebuild that exact call. So I log the request id, the model and version, token counts, latency split into time-to-first-token and total, which retry attempt this was, whether the breaker was open, and which path served the response: model, fallback, or kill switch. The retrieved document ids that went into the context get logged too. Raw secrets never do, and the prompt and the user's content get handled as sensitive data, with the care I gave PII on earlier identity and access projects, because in this product they often are PII.

Token counts and latency are the new query plan. They're the numbers that tell you a prompt change doubled your context size, that one document type is blowing the budget, or that p99 latency is creeping because retrieval got slower and the model didn't. Miss them and you're debugging a nondeterministic system by vibes, which is to say guessing. With them in place, an LLM incident looks like any other production incident: you pull the trace, see the timeout on attempt two with the breaker half-open, and know what happened.

## The same checklist

Timeouts, bounded retries with jitter, a circuit breaker, graceful degradation, a kill switch, and logs you can read. That's the list I'd run against a payment integration or a campus card feed, and nothing on it is new. The one genuine addition is that a 200 can still be a failure, which is why output validation lives inside the reliability work instead of off to the side. Treat the model as the flaky, expensive remote dependency it is, design for its worst day, and the AI part stops being scary. It becomes one more integration you've made boring on purpose.
