---
source_slug: prompt-injection-is-untrusted-input
source_url: https://anthonytadros.me/writing/prompt-injection-is-untrusted-input/
heading: 'Least privilege for tools'
excerpted: 2026-08-17
tampered: false
---

# Prompt injection is just untrusted input
## Least privilege for tools

The injection itself is rarely the damage; the damage is whatever the model can do after it's been talked into something. If the model can only emit text, an injection produces wrong text, which is bad. Wire it to a tool that sends email, deletes records, or makes an authenticated API call, and the same injection hands the attacker your service account. The injection is a foothold, and what the tools can do decides how bad it gets.

This is where old habits pay off. On the remediation work we ran heavy Linux, and the rule was boring: a process gets the narrowest permissions that let it do its job and nothing else. Our tooling didn't run as root because it didn't need root for most of what it did. Tool-calling agents deserve the same treatment. Every tool you expose is an entry in the model's capability list, the model will be coaxed into using all of them eventually, so scope them the way you'd scope a service account.

- Give each tool the minimum scope that makes it useful. A document-search tool reads; it doesn't get a write path 'just in case.'
- Put destructive or outbound actions behind a confirmation the user actually sees, so a silent injection can't trigger them alone.
- Validate the tool arguments the model produces as if a stranger typed them, because in the injection case a stranger did. Path traversal, injection, and unvalidated input are still the failure modes; the model is just a new way to reach them.
- Keep high-trust tools and untrusted retrieved content as far apart in the flow as you can. The more a single turn both reads attacker-controllable text and holds a loaded tool, the worse your day gets.

The dangerous combination is a model that reads untrusted content, has a tool that exfiltrates data, and runs unattended. Read external text, then call a tool that makes a network request. That's the loop that turns a planted instruction in a document into data walking out the door. Break the loop, by gating the tool or by sanitizing what reaches it, and you've defused most of the realistic attacks even though the model stays injectable in principle.
