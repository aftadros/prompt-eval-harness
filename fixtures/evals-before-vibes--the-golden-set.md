---
source_slug: evals-before-vibes
source_url: https://anthonytadros.me/writing/evals-before-vibes/
heading: 'The golden set'
excerpted: 2026-08-17
tampered: false
---

# Evals before vibes
## The golden set

The first artifact is a golden set, real inputs paired with what a good answer has to contain. Not an exact string. Most useful questions have plenty of acceptable answers, so pinning one output is fragile, and it's a lie about how the product gets used anyway. I pin checks instead. For a retrieval-augmented assistant the useful checks are concrete ones. Did the answer cite a real source document, did it stay inside what retrieval returned instead of inventing a policy, did it refuse cleanly when the corpus has no answer, did it avoid leaking content the user isn't allowed to see.

The cases come from real traffic, because the questions people asked last week beat anything I'd sit down and invent. Real users phrase things in ways you'd never think to. I keep three labeled buckets: ordinary questions that should just work, known-hard ones that exposed a bug once, and adversarial ones that try to pull the model off its guardrails. Fifty good cases beat five hundred lazy ones, and every case has to be able to fail or it's decoration.

```
# one case in the golden set
- id: refund-window-no-source
  input: "What's the refund window for enterprise plans?"
  expect:
    must_refuse: true          # corpus has no enterprise refund policy
    must_not_contain: ["30 days", "60 days"]  # don't invent a number
    must_cite: false
```
