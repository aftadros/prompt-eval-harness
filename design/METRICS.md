# METRICS: statistical method spec

Pre-registered: first committed 2026-07-30 (`c0f9c24`), before the first model call against the harness. `git log -p -- design/METRICS.md` shows everything that changed after.

Implementation home: `harness/stats.py`, stdlib-only, every function unit-tested against
externally computed reference values (cite the source of each reference value in a
comment). Bootstrap iterations B = 10,000 with a committed RNG seed, everywhere.

Each entry: formula/procedure, assumptions, the failure mode it protects against, and an
honesty flag at the stated n. **The spec must not promise statistics the n cannot
support**: anything not honestly computable is downgraded to a described limitation
(see the final section). That honesty is deliberate portfolio signal.

## M1. Single-condition pass rate + Wilson 95% CI

p̂ = x/n over cases. Wilson score interval:

    ( p̂ + z²/2n ± z·√( p̂(1−p̂)/n + z²/4n² ) ) / (1 + z²/n),  z = 1.96

- Why Wilson, not Wald or bootstrap: Wald collapses to zero width at p̂ ∈ {0,1}
  (guaranteed to occur in the adversarial bucket); bootstrap adds nothing for a plain
  proportion over independent cases; reserve it for rerun-nested quantities (M4).
- **Anchors to print (verified):** 40/50 → [0.670, 0.888], so a "pass rate of 80%" at n=50
  is ±11 points. Per-bucket at n=15: 12/15 → [0.548, 0.930].
- Protects against: reading a 4-point move as real.

## M2. Estimands, defined once

Per-case pass probability p̂ᵢ = xᵢ/N over N=10 reruns (experiment collections pin N=10).
Three derived outcomes: (a) designated-rerun binary, (b) majority-vote binary, (c) p̂ᵢ
itself. Every analysis states which it uses. **Majority vote destroys flakiness
information; it is a sensitivity analysis, never silently the default** (see M9).

## M3. Paired A/B: exact McNemar

Discordant counts b (A pass, B fail), c (A fail, B pass) on strict-binarized outcomes.

- **Exact (default):** two-sided binomial test of min(b,c) against Bin(b+c, ½), via
  `math.comb`: double the min-tail, cap at 1.
- Chi-square with continuity correction (|b−c|−1)²/(b+c) ~ χ²₁ **only when b+c ≥ 25**
  (at n=50 that essentially never happens). The rule is stated so the code never picks
  the flattering variant.
- Assumptions: cases independent; identical case sets in both arms (enforced by the
  cmp-record precondition); concordant pairs carry no information about the delta; the
  unpaired two-proportion z-test wastes the pairing and is banned in this repo.
- **Power anchors (verified):** 10 discordant pairs need a 9-1 split for p = 0.0215;
  8-2 gives p = 0.109. 6 discordant all one direction: p = 0.031; a single contrary
  flip (7-1) pushes it to p = 0.070. Print these; they are the honest shape of n=50.
- Protects against: H1's exact failure: shipping a delta indistinguishable from noise.

## M4. Paired bootstrap CI on Δ (effect size beside M3's p-value)

For iterations 1..10,000: resample **case indices with replacement**; for each resampled
case take its full rerun record in both arms; compute Δ* = mean(p̂ᵢᴮ) − mean(p̂ᵢᴬ);
report percentile 2.5/97.5.

- **The resample unit is cases, never reruns.** Reruns within a case are correlated
  (case difficulty dominates); resampling reruns manufactures fake n and dishonestly
  shrinks the CI. This sentence appears verbatim in the repo.
- Percentile CI is sufficient; BCa is a documented v2 line.
- Protects against: "p < 0.05" with an effect too small to matter; and the nesting error.

## M5. A/A null calibration: the empirical noise floor

Split prompt A's 10 reruns per case into two disjoint random half-sets of 5; run the
identical comparison pipeline (majority vote per half → McNemar delta; mean-p̂ delta);
repeat 1,000 splits. The distribution of |Δ_AA| **is** "running the same prompt twice";
its 95th percentile is the published noise floor. Real A/B deltas are reported relative
to this floor, not only to the parametric null.

- Protects against: trusting the parametric null when the true rerun process is weirder
  than Bin(N, p): server nondeterminism, batching effects, prompt-cache effects.

## M6. Judge-human agreement: raw %, Cohen's kappa, base-rate table

p_o = (a+d)/n; p_e = Σₖ p_judge,k · p_human,k; κ = (p_o − p_e)/(1 − p_e).
CI: bootstrap over labeled items, B = 10,000, percentile.

**The published-heuristic centerpiece**: what 80% raw agreement (the "disagree on a
fifth of cases" threshold) implies, when both raters' marginal pass rate is π (verified):

| π (pass rate) | p_e | κ at p_o = 0.80 |
|---|---|---|
| 0.50 | 0.500 | 0.600 |
| 0.70 | 0.580 | 0.524 |
| 0.80 | 0.680 | 0.375 |
| 0.85 | 0.745 | 0.216 |
| 0.90 | 0.820 | **−0.111** |

At a 90% pass rate, 80% raw agreement is worse than chance. The threshold is sound at
balanced rates and dangerously lenient at skewed ones. That table is the E3 finding.
Report PABAK = 2p_o − 1 alongside as the balanced-marginals companion.

- **Honesty flag:** SE(κ) at n=75-100 runs ~0.08 (balanced) to 0.16+ (skewed).
  Claimable: coarse bands only, "credibly above 0.4", "credibly below 0.6".
  Not claimable: κ=0.65 vs κ=0.72. Stated here, before data is seen.

## M7. Judge "calibration" at n≈100: the honest substitute

A full reliability diagram + ECE is **not computable honestly here**: 10 bins × ~10
items/bin gives per-bin CIs wider than the diagram's y-axis. Downgraded to a described
limitation with the n that would fix it (~100 labeled items per bin ⇒ n ≈ 1,000).

What runs instead: **consistency-monotonicity.** Judge each labeled item K=10 times;
confidence proxy = max(votes)/K; three coarse bins: unanimous (10/10), strong (8-9),
split (≤7). Question: is judge-vs-human accuracy monotone in bin? Wilson CI per bin.

Rejected alternatives, reasons stated in-repo: verbalized 0-100 confidence (introduces a
new, itself-uncalibrated construct); token logprobs (fragile through LM Studio,
entangled with gpt-oss's reasoning format).

- Protects against: treating a unanimous-but-wrong judge as trustworthy; fake
  calibration curves as portfolio decoration.

## M8. Minimum detectable effect, paired binary (H3's engine)

Primary: **simulation.** Draw n paired outcomes with marginal pass rate p, discordance
rate ψ, true Δ; apply exact M3 at α=0.05; power = rejection rate over 5,000 sims; MDE =
smallest Δ with power ≥ 0.8. Grid: n ∈ {50, 100, 200, 500}, ψ ∈ {0.1, 0.2, 0.3}, plus
the E4 label-noise models. Seed ψ and p from real C1 data once available.

Cross-check: Connor (1987) closed form n = [z₁₋α/₂·√ψ + z₁₋β·√(ψ − Δ²)]² / Δ².
**Anchor (verified):** ψ=0.2, Δ=0.16 → n ≈ 58.9; i.e. at n=50 the binary-outcome MDE is
≈ 0.17 absolute. Using per-case p̂ᵢ (10 reruns) instead of one binary per case roughly
halves that (≈ 0.10 if sd of per-case deltas ≈ 0.25; verify empirically against C1).

- Protects against: the harness implying it can bless 3-point improvements. It cannot;
  the spec says what it can bless.

## M9. Flakiness (H6)

Per-case p̂ᵢ distribution across reruns; classification stable-pass (10/10) /
stable-fail (0/10) / flaky (1-9), per bucket, Wilson CI on flaky share.

- **Stated caveat (verified):** a truly-p=0.95 case shows ≥1 failure in 10 runs with
  probability 0.401, so "flaky" at N=10 includes near-stable cases. Per-case
  Clopper-Pearson intervals printed; the classification is descriptive, not a test.
- **Unstable-case policy feeding H1:** (i) primary: keep them, use p̂ᵢ + case bootstrap,
  which prices flakiness into the CI automatically; (ii) majority vote: sensitivity;
  (iii) exclusion: sensitivity only, clearly labeled, because excluding unstable cases
  changes the estimand to "the stable subpopulation", precisely where regressions hide.

## M10. Score-distribution stats (H5)

Histogram of 1-10 rubric scores; mass on {6,7,8} with case-bootstrap CI; within-output
rerun SD (does the same text get a 6 and an 8?); discrimination put on one fair scale:
dichotomize the 1-10 score at its best threshold and compute κ vs human labels, next to
the binary protocol's κ on the same outputs. (AUC-vs-accuracy across protocols is
apples-to-oranges; dichotomized-κ vs κ is fair.)

- **Framing rule:** descriptive demonstration. No p-value, no "clustering is
  significant"; there is no pre-registered null about the number 7.

## M11. Position bias

Each output pair judged in both orders, 5 reruns per order. Consistency rate (same
winner both orders) with Wilson CI; among inconsistent items, exact binomial test of
first-slot preference vs ½; effect size = per-item slot-1 preference rate with
case-bootstrap CI.

- **Power anchor (verified):** 15 inconsistent items → ≥12/15 one direction for
  p = 0.035. Detects strong bias only; the consistency rate is the always-reportable
  number.

## M12. Verbosity bias

Same-content padding manipulation: script-generated verbose variants of labeled outputs
(content-preserving filler; human spot-checks confirm label inheritance). Judge originals
and padded versions under the identical binary protocol; exact McNemar (M3) on verdict
flips toward the padded version.

- **Anchor (verified):** 12 discordant → ≥10/12 one way for p = 0.039.
- Cleaner than length-regression on observational data: length is manipulated, not
  correlated with quality.

## M13. Self-preference

Leniency gap = P(judge pass | human fail, judge's own family) − P(judge pass | human
fail, other family); Fisher's exact on the 2×2; secondary: overall agreement-rate
difference.

- **Honesty flag:** expected human-fail cells are ~5-15 per family, likely underpowered;
  **declared descriptive-with-CI** unless the gap is enormous. Requires a second model
  family; without one this is not a self-preference probe at all (EXPERIMENTS, E9
  fallback).

## Not honestly computable at these n: publish as limitations

Each appears in the repo's limitations with the n that would repair it:

- ECE / full reliability curves (needs n ≈ 1,000 labels): M7.
- Per-bucket κ (n = 15-25 per bucket).
- κ differences finer than ~0.2.
- E9 self-preference significance at expected cell sizes.
- Per-bucket MDE below "catastrophic" at n=15.
- Any bias-probe × bucket interaction.

## Multiple comparisons

**One flat confirmatory family, Holm-Bonferroni at α = 0.05, membership declared here
before any data collection:**

1. E1 aggregate McNemar (A vs B)
2-4. E2 per-bucket McNemar × 3
5. E5 position directional test
6. E6 verbosity McNemar
7. E9 self-preference Fisher, only if a second family is available; otherwise the
   family has 6 members.

Procedure: sort the m p-values ascending; reject p₍ᵢ₎ while p₍ᵢ₎ ≤ α/(m−i+1). Why Holm:
FWER fits ship/no-ship claims; no independence assumptions; uniformly dominates
Bonferroni; five lines of stdlib Python. Why not BH/FDR: the family is small and each
claim is individually load-bearing.

**Everything else is exploratory or estimation, exempt and labeled:** κ and all CIs
(estimation, no NHST against κ=0, which is trivial); E4 (simulation); E7, E8, M7 bins,
contamination rates (descriptive); any post-hoc slice carries an "exploratory,
uncorrected" tag in code output and writeup alike. House rule: **corrected p-values may
use the word "significant"; nothing else may.**
