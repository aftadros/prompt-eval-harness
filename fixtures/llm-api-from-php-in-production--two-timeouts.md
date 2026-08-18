---
source_slug: llm-api-from-php-in-production
source_url: https://anthonytadros.me/writing/llm-api-from-php-in-production/
heading: 'Two timeouts'
excerpted: 2026-08-17
tampered: false
---

# Calling an LLM API from PHP without taking the page down
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
