---
source_slug: did-the-prompt-change-help
source_url: https://anthonytadros.me/writing/did-the-prompt-change-help/
heading: 'The average is where a regression goes to hide'
excerpted: 2026-08-17
tampered: false
---

# How to tell if a prompt change helped
## The average is where a regression goes to hide

From there it's mechanical. Run the old prompt over the whole set, run the new one, put the two score columns next to each other. The first number I look at is not the overall average, because a change can lift the mean and still be a downgrade if it makes the easy questions a little nicer and one category that matters worse. I've shipped that accident myself. An edit that made the assistant more forthcoming improved a stack of open-ended answers and eroded its willingness to say it doesn't know, which was the behavior I least wanted to lose. The mean went up even though the product got worse, and nothing but the per-category breakdown showed it.

The breakdown has to account for noise too. Model output varies run to run, an LLM judge varies on top of that, and on a small set a one or two point move is usually nothing. I won't ship on a delta I can't tell apart from running the same prompt twice. When a change matters and the set is small, I rerun a few times and check that the improvement holds instead of letting one lucky pass cast the deciding vote.

So I've stopped asking whether the new answer is better; my eye will say yes about my own edit every time. The question the set answers is narrower and duller: did the numbers move, on the cases I decided mattered, by more than the run-to-run noise. That duller question is the only one that has ever stopped me from shipping a prompt that demoed beautifully and made the product worse for everyone who wasn't in the demo.
