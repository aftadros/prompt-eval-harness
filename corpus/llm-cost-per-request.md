---
id: llm-cost-per-request
url: https://anthonytadros.me/writing/llm-cost-per-request/
date: 2026-07-16
title: 'Putting a dollar figure on every model call'
---

# Putting a dollar figure on every model call

The monthly invoice tells you what you spent and nothing about where it went. I price each model call as it happens and store the number on the request, next to latency and error rate.

The invoice at the end of the month is one number, and it's close to useless. It tells you what you spent and nothing about where it went; you can't see which feature is expensive, which tenant is heavy, or whether last week's prompt change cost money or saved it. So I price every model call at the moment it happens and store the result on the request, in the same place I keep latency and error rate.

I've written elsewhere about the levers you pull once you can see the cost. This is about the seeing, which has to come first. The habit comes from years of writing reports against databases, where the bill was paid in wall-clock seconds instead of dollars. You learn fast that "the database is slow" isn't a finding. The finding is which query, run how often, scanning what. A model is the same shape of metered dependency, and "the AI is expensive" is the same non-finding. Attribute the spend to the thing that spent it, or you're staring at a total and guessing.

## One line item per call

Pricing one call is arithmetic, and every input to it is something the provider already hands back. For each request I keep the model and its version, the input tokens split into what was served from the prompt cache and what wasn't, the output tokens, and which path the request took: the cheap model, the expensive one, or an escalation from the first to the second. Each count times its current rate gives the dollar figure for that call.

```
final class CallCost
{
    public function __construct(
        public string $model,
        public int $inputTokens,    // uncached input
        public int $cachedTokens,   // served from the prefix cache
        public int $outputTokens,
        public string $path,        // cheap | smart | escalated | batch
    ) {}

    public function dollars(Rates $r): float
    {
        return ($this->inputTokens  * $r->input
              + $this->cachedTokens * $r->cacheRead
              + $this->outputTokens * $r->output) / 1_000_000;
    }
}
```

The split between cached and uncached input is worth the extra field. Cached input bills at a fraction of the normal rate, so two requests with identical token counts can cost very different amounts depending on how much of the prompt was a stable, reused prefix. Fold input into one number and you've thrown away the biggest swing in the whole calculation.

## Why the unit is the request

I track the per-call number rather than the monthly total because the per-call number can be acted on the same day. A change either moved it or it didn't, and you see which one immediately instead of waiting weeks for an invoice that arrives with everything averaged together. It also survives growth. Traffic doubling roughly doubles the bill and tells you nothing; cost per request drifting up while traffic is flat says some specific feature got more expensive, and points you at it.

Once the per-request cost exists, the slicing falls out of labels the request already carries. Group it by feature and the expensive feature names itself. The same field grouped by endpoint surfaces the one screen building a bloated prompt, and grouped by tenant it surfaces the customer whose traffic all goes to the flagship when half of it could ride the cheap model.

## What it catches

What this catches never shows up in a total. A prompt grows by accretion until one configuration screen is shipping an entire instruction manual in the system message. A refactor moves a per-request value to the top of the prompt, the cache prefix stops matching, and reuse drops to nothing while the cost climbs, with no error to page anyone about. And some spend is structural, like a retrieval feature that runs almost entirely on input tokens because you pack the context with passages and ask for two sentences back. None of it throws an exception. It spends, steadily, until someone reads cost per request by feature and the outlier is sitting in the chart.

The cache one is the worst of these, because it's invisible by design. A broken prefix doesn't crash and doesn't slow anything down; it just charges full freight for input you used to get at a discount, and the only symptom is a number on a dashboard you only have if you built it. I've watched a cache hit rate fall to zero after an innocent refactor and stay there for a while, because nothing was wrong except the bill.

The payoff is that arguments about cost stop being arguments. Nobody has to debate whether caching earns its keep or which model should be the default, because the figure that settles it is already on the dashboard, sliced by the exact thing you're about to change. And it's cheap: one more field on the request log, written next to the latency and the status code.
