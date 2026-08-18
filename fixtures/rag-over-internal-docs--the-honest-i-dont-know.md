---
source_slug: rag-over-internal-docs
source_url: https://anthonytadros.me/writing/rag-over-internal-docs/
heading: 'The honest "I don\'t know"'
excerpted: 2026-08-17
tampered: false
---

# RAG over a decade of internal docs
## The honest "I don't know"

The most important behavior, and the hardest to get, is refusal: when the documentation doesn't cover a question, the assistant has to say so. The default behavior of these models is the opposite. Hand a capable model a vague question and some loosely related passages and it will produce a fluent, plausible answer that's wrong, because fluent and plausible is what it was trained to be. Over real policies that failure does damage, since the wrong answer sounds exactly as confident as a correct one.

Prompt wording alone won't hold that line, so I build refusal in layers. The first layer runs before the model does: if the top retrieval results come back weak or thin, that's a signal to refuse or to narrow the question, and pushing ahead on hope is where the confident wrong answers come from. The prompt itself gives the model explicit permission to say the documents don't cover this, worded so refusing is a normal outcome and nothing discourages it. And once the model has answered, a final check confirms the answer is grounded in the retrieved passages instead of free-floating assertion. Layered checks beat any single clever instruction, the same way one firewall rule doesn't make a system secure.

Refusal is also a tradeoff to own out loud. Tune it too eager and the assistant hallucinates; too cautious and it shrugs at questions it could have answered, which trains people to stop asking. It's a precision/recall dial on trust, and it belongs wherever a wrong answer costs more than a missed one. For documentation people use to make decisions, I lean toward refusing when unsure. "I couldn't find that in the docs" costs someone a trip to a human. A confident wrong answer gets acted on, and the person finds out later.
