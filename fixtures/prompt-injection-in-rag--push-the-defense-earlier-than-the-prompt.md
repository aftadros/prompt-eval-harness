---
source_slug: prompt-injection-in-rag
source_url: https://anthonytadros.me/writing/prompt-injection-in-rag/
heading: 'Push the defense earlier than the prompt'
excerpted: 2026-08-17
tampered: false
---

# Prompt injection in RAG starts with the documents you indexed
## Push the defense earlier than the prompt

The reflex fix is words: a firm line in the system prompt telling the model to disregard any instructions found inside documents. Add the line, and then assume it won't hold. A planted instruction can be more specific, more recent, and more emphatic than your preamble, and the model has no reliable way to decide which one outranks the other. So I move the real work out of the prompt and into retrieval, where I'm writing ordinary code with ordinary control flow instead of negotiating with the model.

The first thing that code does is enforce permissions, before anything gets ranked or assembled into a prompt. In an internal assistant, the identity of the person asking decides what they're allowed to see, and that check belongs at retrieval time. I picked the habit up years ago cleaning sensitive data off machines that were never supposed to hold it; the cheapest way to avoid leaking something is to never load it in the first place. So candidate documents get filtered against the user's access rights first, and restricted material is gone before the reranker or the model ever touches it.

> Restricted text that never enters the context window can't be leaked by an injection, however clever the planted sentence is.

The second thing the code does is remember where each chunk came from. A passage from a public page that got crawled into the index isn't the same risk as a vetted internal policy, and I keep that provenance attached so the low-trust sources draw more suspicion on the way in.

You can also screen retrieved text for the shapes an attack tends to take, like an imperative aimed straight at the assistant, or a line telling it to forget the system prompt. Screening leaks. It catches the lazy attempts and makes the rest more expensive to pull off.
