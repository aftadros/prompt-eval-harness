---
source_slug: llm-cost-per-request
source_url: https://anthonytadros.me/writing/llm-cost-per-request/
heading: 'One line item per call'
excerpted: 2026-08-17
tampered: false
---

# Putting a dollar figure on every model call
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
