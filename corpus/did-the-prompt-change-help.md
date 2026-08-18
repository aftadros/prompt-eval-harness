---
id: did-the-prompt-change-help
url: https://anthonytadros.me/writing/did-the-prompt-change-help/
date: 2026-07-21
title: 'How to tell if a prompt change helped'
---

# How to tell if a prompt change helped

One better answer on the example you picked is one biased data point. I run the old and new prompts over a fixed set of real questions and read the per-category delta before the edit ships.

You change a prompt, rerun the question you've been staring at all afternoon, and the answer comes back better. That's about as biased as a data point gets: you tested one case, which you picked, hoping the edit you'd just written would win. An improvement there means the change can help on that example. Whether it helped in general is a question one example can't answer, however good the answer looks.

The prompt edits I ship face a wide spread of real questions, most of which I'll never personally try. I stopped trusting the demo a while ago. Instead I keep a fixed set of questions and compare how the old prompt and the new one did across the whole set, rather than on the single case that prompted the edit.

## Build the set from real questions, including the ones that failed

The set doesn't need to be large to be useful. A few dozen questions that look like your real traffic beat a thousand synthetic ones. Mine is seeded from production and weighted toward the categories that matter, plus the specific cases that have burned me before. Every time someone reports a bad answer, that question goes in with a note about what a good answer would have been, so the bug becomes a permanent test. Over time the set turns into a record of every way the thing has been wrong, which is the record you want standing between a prompt edit and your users.

Each question needs something to check against, and it doesn't have to be a gold answer. Sometimes it's a reference response. More often it's a property the answer either has or doesn't: a cited source, a refusal where refusing was the right call, valid JSON, a fact I know belongs in there. Properties are cheaper to write than a model-graded rubric and far cheaper to run, and they don't drift between runs. So I lean on them anywhere the question allows and save the fuzzy grading for the answers that need real judgment.

## The average is where a regression goes to hide

From there it's mechanical. Run the old prompt over the whole set, run the new one, put the two score columns next to each other. The first number I look at is not the overall average, because a change can lift the mean and still be a downgrade if it makes the easy questions a little nicer and one category that matters worse. I've shipped that accident myself. An edit that made the assistant more forthcoming improved a stack of open-ended answers and eroded its willingness to say it doesn't know, which was the behavior I least wanted to lose. The mean went up even though the product got worse, and nothing but the per-category breakdown showed it.

The breakdown has to account for noise too. Model output varies run to run, an LLM judge varies on top of that, and on a small set a one or two point move is usually nothing. I won't ship on a delta I can't tell apart from running the same prompt twice. When a change matters and the set is small, I rerun a few times and check that the improvement holds instead of letting one lucky pass cast the deciding vote.

So I've stopped asking whether the new answer is better; my eye will say yes about my own edit every time. The question the set answers is narrower and duller: did the numbers move, on the cases I decided mattered, by more than the run-to-run noise. That duller question is the only one that has ever stopped me from shipping a prompt that demoed beautifully and made the product worse for everyone who wasn't in the demo.
