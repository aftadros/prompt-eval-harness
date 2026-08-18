---
source_slug: evals-before-vibes
source_url: https://anthonytadros.me/writing/evals-before-vibes/
heading: 'What this looks like on a normal week'
excerpted: 2026-08-17
tampered: false
---

# Evals before vibes
## What this looks like on a normal week

The payoff is mundane, which is the point. A ticket comes in to make the assistant more concise. I write the instruction, run the harness, and conciseness improves while the grounding check drops four points, because a shorter answer stopped citing its source. Without the harness, that ships and comes back as a bug report. In the diff it was just a visible tradeoff, so I tightened the instruction and reran until conciseness and grounding both held. It's the same loop I've used for years making integrations behave. I change one thing and let the measurement decide whether it stays.

None of this needs a platform. The first version is a script, a YAML file of cases, and a results file you commit next to the code. A fancier harness can come later, once the discipline exists and you know what you're measuring. Teams that buy tooling first end up with a dashboard nobody trusts and decisions still made on vibes.

A change that feels better is still where I start. But the demo question was always going to look good; the harness is for the hundred I didn't type.
