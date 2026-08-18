---
source_slug: prompt-injection-in-rag
source_url: https://anthonytadros.me/writing/prompt-injection-in-rag/
heading: 'The prompt and the output'
excerpted: 2026-08-17
tampered: false
---

# Prompt injection in RAG starts with the documents you indexed
## The prompt and the output

Inside the prompt I still do the hygiene. Retrieved context goes in a clearly marked region, walled off from the instructions, so the model has some structural help telling data from commands. That lowers the success rate without being a guarantee, which is the most I expect from any model-level mitigation here.

The output is untrusted for the same reason the input was, and I've written about that side on its own. Retrieval changes the route: an attacker doesn't need the user's keyboard, because any document you were willing to index will do. So a successful injection needs somewhere useful to go, and I try not to give it one. Answers get escaped before they render. Any tool the assistant can reach is scoped down to read-only, with the narrowest reach that still does the job, and I keep retrieval far away in the flow from anything that can send data outward. A planted sentence with no exit mostly fizzles.

None of this makes the model safe to point at arbitrary text. The aim is narrower, keeping one planted instruction from being fatal. The permission filter is the load-bearing piece, because the worst sentence in the corpus still can't reach data the user was never cleared for; everything else just runs up the attacker's cost. I wouldn't put an assistant over documents I didn't control, and I stay a little nervous even over the ones I supposedly do, because the documents I 'control' include the wiki that anyone in the company can edit.
