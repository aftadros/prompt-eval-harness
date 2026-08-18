---
id: llm-api-from-php-in-production
url: https://anthonytadros.me/writing/llm-api-from-php-in-production/
date: 2026-07-06
title: 'Calling an LLM API from PHP without taking the page down'
---

# Calling an LLM API from PHP without taking the page down

Nearly everything written about running LLMs in production assumes Python. This is the plumbing I use on a PHP and Kubernetes platform so a provider's bad day doesn't take the page down.

Almost everything written about putting language models into production assumes you're writing Python. The tutorials reach for a framework and the retry helper is one import away. The streaming example is Node. I ship LLM features on a PHP and Kubernetes platform, so I get to reinvent a lot of that from first principles. The good news is that none of it is new. A model endpoint is a slow, flaky, metered remote dependency, and PHP has been calling slow, flaky remote dependencies for as long as PHP has existed. The whole trick is to quit treating the model as special and call it the way you'd call any other integration that can have a bad day.

I've spent a decade wiring external systems into a platform that has to stay up, and the model call gets the same suspicion I give a customer's directory feed or a payment gateway. It'll be slow or down on the wrong day, and when it does answer, the answer can still be wrong. Most of the code below is Guzzle, which is what I reach for.

## Two timeouts

The most common mistake is one timeout, or none. A model call has two failure modes that look nothing alike. The provider might be unreachable, and you want to give up on that in a second or two and move on. Or it's reachable but slow to finish generating, and you're willing to wait longer, because a real answer is coming. Guzzle lets you separate the two, and you should.

```
$client = new GuzzleHttp\Client([
    'base_uri'        => 'https://api.provider.example',
    'connect_timeout' => 2,    // can't even reach them: fail fast
    'timeout'         => 30,   // total ceiling for a non-streaming call
]);
```

The 2 is the outage tripwire; the 30 is how long I'm willing to wait for a real answer to finish generating. Streaming changes what the total means, since the connection stays open while tokens arrive, so you end up bounding the idle gap between chunks instead of the whole call. Either way the number is a decision. I pick it from what the feature can tolerate, and I write it down where the next person will find it.

## Which failures to retry

Retrying is where well-meaning code does real damage. Retrying a malformed request just buys the same 400 twice, and with no ceiling on attempts, one slow provider becomes an outage of your own making, plus a bill. My rule is narrow: retry transient failures, meaning connection errors, timeouts, 429 rate limits, and 5xx responses. Everything else fails immediately. A retry won't change the answer.

```
use GuzzleHttp\HandlerStack;
use GuzzleHttp\Middleware;
use GuzzleHttp\Exception\ConnectException;
use Psr\Http\Message\RequestInterface;
use Psr\Http\Message\ResponseInterface;

$stack = HandlerStack::create();
$stack->push(Middleware::retry(
    function (int $attempt, RequestInterface $req, ?ResponseInterface $res = null, ?Throwable $err = null): bool {
        if ($attempt >= 3) return false;                 // hard cap
        if ($err instanceof ConnectException) return true;
        $status = $res ? $res->getStatusCode() : 0;
        return $status === 429 || $status >= 500;        // transient only
    },
    function (int $attempt, ?ResponseInterface $res = null): int {
        if ($res && $res->hasHeader('Retry-After')) {    // obey the provider first
            return ((int) $res->getHeaderLine('Retry-After')) * 1000;
        }
        return (int) ((2 ** $attempt) * 250 + random_int(0, 250)); // backoff + jitter, ms
    }
));
```

Two details in there are worth calling out. The jitter, the small random number added to the backoff, keeps a fleet of pods from retrying in lockstep against a provider that's already struggling. And honoring Retry-After means that when the provider tells you exactly how long to wait, you wait that long instead of guessing. Both are cheap courtesy, and they keep you off a rate-limit blocklist.

## A deadline on the whole operation

There's a trap waiting right behind the retries. Three attempts against a thirty-second timeout is, in the worst case, ninety seconds plus backoff before your fallback ever fires. You added resilience and made the bad case worse, because the user left at second eight. Retries improve the odds for a single call and do nothing at all for the person waiting on it. So I put a deadline around the entire operation, separate from the per-call timeout, and when the deadline passes I stop retrying and degrade.

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

## A 200 is not success

This one is new with LLMs, and PHP developers are well placed to get it right, because we've spent careers escaping output. A model can return a clean 200 with a body that's malformed, off-topic, or hostile, and the HTTP layer will file that under success. So the response is untrusted input from the moment it arrives. If you asked for JSON, parse and validate it against a schema before anything downstream touches it, and treat a parse failure as a retryable error rather than a crash. If the text will be rendered, escape it like any user-supplied string, because a model that read an attacker's document can echo an attacker's script. Output validation belongs on the reliability surface next to the timeouts, not off in a security backlog.

## Fallback and kill switch

Every model-backed feature I ship has a defined behavior for when the model is unavailable, and a flag that forces that behavior without a deploy. The fallback is whatever still helps with no model in the loop: a cached previous answer, a plain non-AI path, or an honest message that the smart version is off. The kill switch is a single config value, read on every request with no caching that would delay it, so when a prompt change misbehaves or costs spike I can turn the feature off in seconds and debug calmly. A kill switch you've never flipped is a guess, which is why the off state is a real, tested mode and not an error.

## Log enough to reconstruct one call

Nondeterminism is what makes these bugs miserable, and logging is how you claw the ground back. For every call I record a request id, the model and version, input and output token counts, latency split into time-to-first-token and total, which retry attempt this was, whether the breaker was open, and which path served the response: model, fallback, or kill switch. I don't log secrets, and I treat the prompt and the user content as sensitive, because on this product they often are. With those fields an LLM incident stops being a vibe and becomes an ordinary production incident. You pull the trace, you see the timeout on attempt two with the breaker half-open, and you know what happened.

> Treat the model as the flaky, expensive remote dependency it is, design for its worst day, and the AI part stops being scary. It's one more integration made boring on purpose.

Nothing here needed Python. Two timeouts, transient-only retries with jitter, a deadline on the operation, a circuit breaker, output you validate instead of trusting, a fallback, a kill switch, logs you can read: it's the checklist I'd run on a payment integration or a campus card feed, with one extra line for the fact that a successful response can still be a failure.
