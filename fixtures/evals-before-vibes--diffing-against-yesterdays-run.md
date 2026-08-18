---
source_slug: evals-before-vibes
source_url: https://anthonytadros.me/writing/evals-before-vibes/
heading: "Diffing against yesterday's run"
excerpted: 2026-08-17
tampered: false
---

# Evals before vibes
## Diffing against yesterday's run

Once the set exists the harness is a loop. Run every case through the current configuration, apply each check, write the pass and fail counts to a file, and diff that file against the last run. I mostly ignore the score and read the diff. Five cases that passed yesterday and fail today is a regression with a name on it, and I can open each one and read the new output next to the old before anyone outside the team sees it.

That reframes prompt work the way version control reframed code. The unit becomes the change and its measured effect. I keep the harness fast and boring on purpose so it runs on every prompt edit, the same way I lean on a release pipeline to tell me a build is bad before it ships rather than after a customer files a ticket. A slow eval that runs once a sprint gets skipped under deadline, right when you need it most.

- Pin the model version and decoding settings in the run record; a score with no model attached to it means nothing.
- Run each case more than once when temperature is nonzero. A check that passes 3 of 5 times is data, and a single green run hides it.
- Store every raw output alongside the pass or fail result, because when a number moves you'll want to read the text rather than rerun and hope it reproduces.
- Treat a flaky case as a finding. Either the check is too strict or the behavior really is unstable, and both are worth knowing.
