---
source_slug: prompt-injection-is-untrusted-input
source_url: https://anthonytadros.me/writing/prompt-injection-is-untrusted-input/
heading: 'Defense in depth'
excerpted: 2026-08-17
tampered: false
---

# Prompt injection is just untrusted input
## Defense in depth

None of this makes prompt injection go away. It's a real, open problem, and the model providers will tell you so themselves. The point of the layers is that no single one has to hold. An injection that gets past the delimiters and the provenance checks still meets least-privilege tools; an answer it manages to poison still gets escaped before it reaches anything downstream. Guardrails on the way in and the way out, plus enough logging that when something slips through, you can find the seam it used.

That's defense in depth, the only approach I've seen hold up anywhere in security. No single layer gets trusted with the whole job.

In an earlier support role I kept QA above 90% while the floor sat near 60%, and the difference was never one clever trick. It was checking the boring things every time. AI systems reward the same temperament. The model gives you the flashy demo for free. Whether the thing survives real users depends on whether somebody assumed the input was lying, and appsec has been assuming that for thirty years.
