---
source_slug: llm-api-from-php-in-production
source_url: https://anthonytadros.me/writing/llm-api-from-php-in-production/
heading: 'A circuit breaker for the hard-down case'
excerpted: 2026-08-17
tampered: false
---

# Calling an LLM API from PHP without taking the page down
## A circuit breaker for the hard-down case

Retries handle one unlucky call. They're the wrong tool when the provider is hard down, since every request then pays the full timeout-and-retry tax before failing, and one outage becomes a pile of slow requests holding your PHP-FPM workers hostage. A circuit breaker fixes that. After enough failures it opens, and while it's open you skip the call entirely and go straight to the fallback. PHP has no built-in breaker, but a small one over any shared cache, APCu or Redis, is a few lines.

```
final class Breaker
{
    public function __construct(
        private Psr\SimpleCache\CacheInterface $cache,
        private string $key,
        private int $threshold = 5,
        private int $cooldown = 30,
    ) {}

    public function allow(): bool {
        return time() >= (int) $this->cache->get($this->key.':open_until', 0);
    }
    public function success(): void { $this->cache->delete($this->key.':fails'); }
    public function failure(): void {
        $fails = (int) $this->cache->get($this->key.':fails', 0) + 1;
        $this->cache->set($this->key.':fails', $fails, 60);
        if ($fails >= $this->threshold) {
            $this->cache->set($this->key.':open_until', time() + $this->cooldown, $this->cooldown);
        }
    }
}
```

```
if (! $breaker->allow()) {
    return $this->fallback();          // open: don't even dial
}
try {
    $answer = $this->callModel($prompt);
    $breaker->success();
    return $answer;
} catch (Throwable $e) {
    $breaker->failure();
    return $this->fallback();
}
```

When the cooldown passes, the next request is a probe. If it works the breaker resets; if it fails the cooldown starts over. Nobody needs the state machine to be elegant. What it buys you is a page that stays fast during a real outage, because it stops waiting on something it already knows is broken. If you run more than one provider, an open breaker is also your cue to fail over to the backup instead of the fallback, the same pattern with a different branch.
