---
source_slug: did-the-prompt-change-help
source_url: https://anthonytadros.me/writing/did-the-prompt-change-help/
heading: 'Build the set from real questions, including the ones that failed'
excerpted: 2026-08-17
tampered: false
---

# How to tell if a prompt change helped
## Build the set from real questions, including the ones that failed

The set doesn't need to be large to be useful. A few dozen questions that look like your real traffic beat a thousand synthetic ones. Mine is seeded from production and weighted toward the categories that matter, plus the specific cases that have burned me before. Every time someone reports a bad answer, that question goes in with a note about what a good answer would have been, so the bug becomes a permanent test. Over time the set turns into a record of every way the thing has been wrong, which is the record you want standing between a prompt edit and your users.

Each question needs something to check against, and it doesn't have to be a gold answer. Sometimes it's a reference response. More often it's a property the answer either has or doesn't: a cited source, a refusal where refusing was the right call, valid JSON, a fact I know belongs in there. Properties are cheaper to write than a model-graded rubric and far cheaper to run, and they don't drift between runs. So I lean on them anywhere the question allows and save the fuzzy grading for the answers that need real judgment.
