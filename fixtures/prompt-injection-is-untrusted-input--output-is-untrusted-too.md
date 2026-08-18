---
source_slug: prompt-injection-is-untrusted-input
source_url: https://anthonytadros.me/writing/prompt-injection-is-untrusted-input/
heading: 'Output is untrusted too'
excerpted: 2026-08-17
tampered: false
---

# Prompt injection is just untrusted input
## Output is untrusted too

Appsec has a phrase for the other half: filter input, escape output. The escape half gets forgotten in AI systems constantly. Whatever the model produces is also untrusted, since it may be parroting an injection or hallucinating something dangerous on its own. Render model output as HTML and you've got an XSS sink; feed it into a shell, a SQL query, or another tool call and you've got command injection with extra steps. The model is an input source to the rest of your stack, and you escape its output the same way you'd escape anything coming off the wire.

I've watched teams spend all their effort hardening the prompt, then pipe the raw completion into a markdown renderer that happily executes embedded scripts. That's validating the form on the client and trusting it on the server. The trust boundary sits wherever data moves between components, and the model's output crosses one every time it hands a string to your application code.
