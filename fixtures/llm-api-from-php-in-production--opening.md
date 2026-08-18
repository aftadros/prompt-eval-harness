---
source_slug: llm-api-from-php-in-production
source_url: https://anthonytadros.me/writing/llm-api-from-php-in-production/
heading: 'Opening'
excerpted: 2026-08-17
tampered: false
---

# Calling an LLM API from PHP without taking the page down
## Opening

Almost everything written about putting language models into production assumes you're writing Python. The tutorials reach for a framework and the retry helper is one import away. The streaming example is Node. I ship LLM features on a PHP and Kubernetes platform, so I get to reinvent a lot of that from first principles. The good news is that none of it is new. A model endpoint is a slow, flaky, metered remote dependency, and PHP has been calling slow, flaky remote dependencies for as long as PHP has existed. The whole trick is to quit treating the model as special and call it the way you'd call any other integration that can have a bad day.

I've spent a decade wiring external systems into a platform that has to stay up, and the model call gets the same suspicion I give a customer's directory feed or a payment gateway. It'll be slow or down on the wrong day, and when it does answer, the answer can still be wrong. Most of the code below is Guzzle, which is what I reach for.
