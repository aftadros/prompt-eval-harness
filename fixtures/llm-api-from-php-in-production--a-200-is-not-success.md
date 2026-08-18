---
source_slug: llm-api-from-php-in-production
source_url: https://anthonytadros.me/writing/llm-api-from-php-in-production/
heading: 'A 200 is not success'
excerpted: 2026-08-17
tampered: false
---

# Calling an LLM API from PHP without taking the page down
## A 200 is not success

This one is new with LLMs, and PHP developers are well placed to get it right, because we've spent careers escaping output. A model can return a clean 200 with a body that's malformed, off-topic, or hostile, and the HTTP layer will file that under success. So the response is untrusted input from the moment it arrives. If you asked for JSON, parse and validate it against a schema before anything downstream touches it, and treat a parse failure as a retryable error rather than a crash. If the text will be rendered, escape it like any user-supplied string, because a model that read an attacker's document can echo an attacker's script. Output validation belongs on the reliability surface next to the timeouts, not off in a security backlog.
