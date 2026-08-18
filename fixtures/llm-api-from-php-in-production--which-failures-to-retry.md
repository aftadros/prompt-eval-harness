---
source_slug: llm-api-from-php-in-production
source_url: https://anthonytadros.me/writing/llm-api-from-php-in-production/
heading: 'Which failures to retry'
excerpted: 2026-08-17
tampered: false
---

# Calling an LLM API from PHP without taking the page down
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
