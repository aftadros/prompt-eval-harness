<!-- Working spec, 2026-07-27. Publication decision per-file at M0 (see DECISIONS.md).
     Commit this file (with METRICS.md) BEFORE collection C1 runs — pre-registration flavor.
     Design pressure-tested with Claude. -->

# EXPERIMENTS — the writeup's experiment suite

Thesis: the practitioner heuristics published in *Evals before vibes* and *How to tell
if a prompt change actually helped*, put under statistical test on the author's own
corpus. Confirmations and refutations are equally publishable; the refutations are the
better chapters.

## Design constants

- Golden set: 50 cases — 20 ordinary / 15 known-hard / 15 adversarial (see CORPUS.md).
- Reruns: **N = 10** per case per condition, temperature 0.7 (nonzero on purpose —
  flakiness must be able to exist), top_p / max_tokens pinned, seed recorded but not
  trusted (verify LM Studio's actual seed behavior before C1; observed near-determinism
  is itself an E1/E8 datum). All raw outputs committed under `runs/`.
- Outcomes: per-case deterministic-check conjunction (pass/fail); ~15 judge-routed cases
  add binary verdicts under the published protocol (one narrow yes/no, source in hand,
  verdict before explanation).
- Workhorse + judge: gpt-oss-120b, local, free. **Second family (E9 only):** any
  non-OpenAI-family local GGUF — suggest a Qwen instruct model in LM Studio, still free.
  Fallback if genuinely unavailable: gpt-oss-20b, but the probe must be renamed
  "size-asymmetry within family" and self-preference declared untestable.
- Prompt pair: **P_A** = grounded-QA baseline. **P_B** = P_A plus the "be more
  forthcoming / avoid unnecessary refusals" edit — deliberately the edit from the
  published anecdote, chosen because it plausibly lifts ordinary-bucket scores while
  eroding no-answer refusals and injection resistance. Designing P_B to *plausibly*
  produce that pattern is legitimate and is disclosed; whether it actually does is the
  experiment.

## Data collections — 3 model-call collections + 1 labeling pass feed all 9 analyses

Do not design nine separate data collections; these four feed everything.

| ID | Contents | Calls | Feeds |
|---|---|---|---|
| **C1** core grid | 50 cases × {P_A, P_B} × 10 reruns, fixtures on | 1,000 gen | E1, E2, E8; empirical ψ/p for M8; outputs for all judge work |
| **C2** closed-book + family-2 | 50 cases × 5 closed-book (no fixtures); 25-case stratified subset × 5 reruns on family-2 | ~375 gen | contamination probe; E9 |
| **C3** judge grid | binary judge on judge-routed C1 outputs (m=5); K=10 on all labeled items; 1–10 rubric on 50 labeled outputs × 10; pairwise both-orders 50 pairs × 2 × 5; padded variants 40 × 5; family-2 outputs 25 × 5 | ~3,800 short | E3, E5, E6, E7, E9, M7 |
| **L1** labeling | 100 items, blinded (protocol in CORPUS.md): 50 P_A outputs (all cases) / 25 family-2 subset / 15 largest-\|Δ\| flip cases from P_B / 10 padding spot-checks | human | E3, E7, E9, flip adjudication |

Rig cost: wall-clock only. Measure tok/s first; at ~300–600-token generations and
~100-token verdict-first judge calls, C1 ≈ one overnight batch, C3 ≈ a second, C2 ≈ 1–2h.
The `~/bin/llmbatch` concurrency pattern applies. **Total: 2–3 overnight batches, $0.**

## Experiments, ordered by writeup value

### E1 (flagship). "Don't ship on a delta you can't tell apart from running the same prompt twice"
- **Hypothesis:** plausible-looking A/B deltas frequently fall inside both the exact-
  McNemar null and the empirical A/A noise floor.
- **Design:** C1. Primary: exact McNemar (M3) on strict-binarized outcomes + paired
  bootstrap CI (M4) on per-case p̂ deltas. Noise floor: M5 A/A splits.
- **Sample-size math:** MDE ≈ 0.17 (binary) / ≈ 0.10 (per-case p̂) at n=50 — printed in
  the writeup as "what this harness can and cannot detect."
- **Confirm:** shippable-looking deltas land inside the A/A band — the heuristic has
  teeth. **Refute:** the A/A floor ≈ 0 (near-deterministic local reruns), making the
  heuristic vacuous on this rig — an honest, interesting result about local inference;
  the parametric test remains the binding constraint.
- **Cost:** shares C1; analysis is seconds.

### E2. "The average is where a regression goes to hide"
- **Hypothesis:** P_B's aggregate delta is ≥ 0 or CI-straddling while the adversarial
  bucket regresses significantly one-directionally.
- **Design:** C1; per-bucket exact McNemar ×3 in the Holm family, plus the aggregate.
- **Sample-size math (verified):** at n=15 adversarial, 6 discordant all one direction
  gives p = 0.031; a single contrary flip (7–1) gives p = 0.070. Only near-catastrophic
  bucket regressions are detectable — and that is the narrative: real eval buckets are
  small, and a real refusal-collapse still clears the bar.
- **Confirm:** aggregate flat-or-up, adversarial significantly down after Holm, and the
  15 human-adjudicated flip cases read as real regressions. **Refute:** the regression
  shows in the aggregate too, or no bucket regression materializes — report the honest
  null; the heuristic's demonstration would need a different edit.
- **Cost:** shares C1.

### E3. "Grade the grader" and the fifth-of-cases threshold
- **Hypothesis:** judge-vs-human κ is estimable in coarse bands at n≈100, and the "80%
  raw agreement" cutoff maps to wildly different κ across base rates (M6 table).
- **Design:** L1 labels vs judge majority verdicts (K=10) on the same items; raw %, κ +
  bootstrap CI, PABAK; the M6 table recomputed at the observed base rate; M7
  consistency-monotonicity as the calibration substitute.
- **Sample-size math:** raw agreement at n=100: Wilson ±~0.08 around 0.80 — distinguishes
  "clearly ≥0.8" from "clearly ≤0.7", nothing finer; κ in coarse bands only (pre-stated).
- **Confirm:** at the observed base rate the threshold implies κ ≳ 0.5 — survives for
  this operating point, with the table showing where it breaks. **Refute:** observed base
  rate ≥ 0.85, where 80% agreement implies κ ≤ 0.22 — the heuristic needs a
  base-rate-aware restatement. **The restatement is the deliverable either way.**
- **Cost:** shares C3 + L1; the real cost is the labeling session (~4–5h human time).

### E4. "Fifty good cases beat five hundred lazy ones"
- **Hypothesis (as published):** n=50 clean labels detect what n=500 noisy labels miss.
- **Design:** pure simulation (M8), parameterized by C1's empirical p and ψ. Two noise
  models: (a) symmetric random label flips at ε ∈ {0, .05, .1, .2, .3}; (b) systematic
  bias — a lazy labeler auto-passes long/confident answers (directional flips on a
  correlated subset).
- **The math that makes this the best chapter (verified):** under symmetric noise,
  Δ_obs = (1−2ε)Δ and effective n ≈ n(1−2ε)²; n=500 falls below n=50-clean only at
  ε ≈ 0.34 (500 × (1−0.68)² = 51.2). So **as a variance claim the heuristic is likely
  refuted** — 500 mediocre labels usually out-power 50 clean ones. Under systematic
  bias, no n helps: n=500 confidently detects a *wrong* delta. **The heuristic is wrong
  about variance and right about bias**, and the writeup says exactly that.
- **Cost:** zero model calls; minutes of CPU.

### E5. Position bias (order-swap) — grounded in arXiv 2410.02736
- **Hypothesis:** the judge's pairwise winner depends on slot order.
- **Design:** C3 pairwise block — 50 A-vs-B output pairs × both orders × 5 reruns. M11.
- **Confirm:** consistency < ~85% and the directional test survives Holm. **Refute:**
  high consistency, no direction — reported as "not detectable at this n and model,"
  never "no bias."
- **Writeup beat:** this is exactly why the harness's primary protocol is absolute
  yes/no per output, not pairwise — the probe justifies the protocol.
- **Cost:** ~500 short calls, shares C3.

### E6. Verbosity bias (length-controlled) — same grounding
- **Hypothesis:** identical content, padded, flips fail→pass more than pass→fail.
- **Design:** M12 — 40 padded pairs judged under the production binary protocol; exact
  McNemar. Padding script must not alter factual content — 10 human spot-checks (L1).
- **Confirm:** asymmetric flips toward padded. **Refute:** symmetric/none — evidence the
  narrow yes/no criterion resists verbosity, a pro-protocol result feeding E7.
- **Cost:** ~200 short calls + padding script.

### E7. "A bare 1-to-10 judge score clusters around 7"
- **Hypothesis:** naive-rubric mass concentrates on {6,7,8}, with low within-output
  consistency and no more discrimination than the binary protocol.
- **Design:** M10 on the 50 labeled P_A outputs, 10 rubric reruns each, vs the binary
  protocol's κ on identical outputs.
- **Confirm:** ≥50% mass on {6,7,8}, rerun SD ≥ ~1 point, dichotomized-κ ≤ binary-κ.
  **Refute:** well-spread, stable, more discriminative. Explicitly exploratory framing.
- **Cost:** ~500 short calls, shares C3.

### E8. Rerun flakiness is a finding
- **Hypothesis:** flakiness concentrates in known-hard/adversarial buckets, and ignoring
  it (majority vote) materially narrows the E1 CI.
- **Design:** M9 on C1 P_A; then the three unstable-case policies side by side as the
  sensitivity table (keep-with-bootstrap / majority-vote / exclusion).
- **Confirm:** nonuniform flaky share; visibly different A/B CIs across policies
  (exclusion flattering). **Refute:** flakiness uniform and immaterial — then the
  finding is "at pinned local decoding, flakiness is negligible," which bounds the
  heuristic's domain.
- **Cost:** shares C1.

### E9. Self-preference — grounded in arXiv 2410.21819
- **Hypothesis:** gpt-oss-120b as judge passes human-failed outputs from its own family
  more often than from family 2.
- **Design:** M13 on the 25-case subset: own-family outputs (C1) vs family-2 outputs
  (C2), judged identically, conditioned on the L1 labels covering both.
- **Declared descriptive** (expected human-fail cells 5–15 per family); Fisher exact
  reported but the writeup leads with the gap + CI and the n that would resolve it
  (~100 human-failed cases per family). Runs as a true self-preference probe only with
  a second family loaded.
- **Cost:** shares C2/C3.

## Contamination

Two distinct things, kept separate because conflating them is the common error:

1. **By-construction overlap (not contamination):** golden questions are authored from
   the same 11 posts that are the fixtures. That is the definition of closed-corpus
   grounded QA, not leakage — but it scopes every claim to "this assistant on this
   corpus." The methods are corpus-agnostic; the portfolio thesis lives in the methods.
2. **Pretraining exposure (actual contamination):** the posts are public (June 2026) and
   may sit in gpt-oss's training window. The model may answer from weights: "grounded"
   pass rates then partially measure recall, and no-answer refusal cases are
   contaminated in the worst direction (the model may "know" an answer the fixtures
   don't contain).

**Detection probe (C2, ~250 calls):** closed-book condition — same 50 questions, no
fixtures, "answer from your own knowledge," scored by the same deterministic checks;
5 reruns per case. Report the **contamination-or-guessability rate** (share of cases
passable closed-book, Wilson CI). Optional refinement at zero labeling cost: entity-swap
a handful of closed-book-passable questions; surviving accuracy indicates
prior-guessable rather than memorized.

**Use in results:** primary analyses run on all cases with the rate disclosed up front;
each headline gets a sensitivity row excluding closed-book-passable cases; the no-answer
adversarial cases get a dedicated sentence (their closed-book behavior reported
verbatim). Scoping line for the writeup: retrieval-grounding claims are attenuated by
the measured closed-book rate; **the statistical machinery — paired tests, noise floors,
kappa, power maps — is unaffected by contamination, which is precisely why the repo is
about the machinery.**

## Sequencing

1. Freeze `cases/` + `fixtures/` + `checks/`.
2. Commit METRICS.md + EXPERIMENTS.md (pre-registration — cheap, high-signal).
3. C1 overnight → E1/E2/E8. C2 (+ family-2 download) → contamination, E9 inputs.
   C3 overnight → judge analyses.
4. L1 blinded labeling session → E3/E7/E9 and flip adjudication.
5. E4 simulation anytime (no model calls).

Judge-routed case list must be fixed before seeing results — no outcome-shopping.
