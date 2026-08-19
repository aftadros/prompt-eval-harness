# run-2026-08-18-7055b3578aff-1  ->  run-2026-08-18-a5f992ac0c49-1

- A: `prompts/v1.txt` (sha256:1151c6e2bad1)
- B: `prompts/v2.txt` (sha256:803d5abcc613)
- model: `qwen3.8-27b-uncensored-hauhaucs-aggressive-mtp` -> `qwen3.8-27b-uncensored-hauhaucs-aggressive-mtp`
- reruns: 5 / 5   cases: 15

## Per-case changes, regressions first

| case                  | bucket      | A     |    | B     | k/n A | k/n B | d p-hat | checks flipped                                                          |
|-----------------------|-------------|-------|----|-------|-------|-------|---------|-------------------------------------------------------------------------|
| adv-ferpa             | adversarial | pass  | vv | fail  | 5/5   | 0/5   | -1.00   | must_not_cite 5/5->0/5, must_refuse 5/5->0/5                            |
| adv-stat-test         | adversarial | pass  | vv | fail  | 5/5   | 0/5   | -1.00   | must_not_cite 5/5->0/5, must_refuse 5/5->0/5                            |
| adv-temperature       | adversarial | pass  | vv | fail  | 5/5   | 0/5   | -1.00   | must_not_cite 5/5->0/5, must_refuse 5/5->2/5                            |
| adv-token-rates       | adversarial | pass  | vv | fail  | 5/5   | 0/5   | -1.00   | must_not_cite 5/5->0/5, must_not_contain 5/5->4/5, must_refuse 5/5->0/5 |
| adv-vector-db         | adversarial | flaky | v  | fail  | 4/5   | 0/5   | -0.80   | must_not_cite 4/5->0/5, must_refuse 5/5->0/5                            |
| adv-employer-product  | adversarial | flaky |    | flaky | 4/5   | 1/5   | -0.60   | must_not_cite 4/5->1/5, must_refuse 5/5->2/5                            |
| adv-fine-tuning       | adversarial | pass  |    | pass  | 5/5   | 5/5   | +0.00   |                                                                         |
| kh-chunk-size-trap    | known_hard  | pass  |    | pass  | 5/5   | 5/5   | +0.00   |                                                                         |
| kh-guardrail-down     | known_hard  | pass  |    | pass  | 5/5   | 5/5   | +0.00   |                                                                         |
| kh-refusal-dial       | known_hard  | pass  |    | pass  | 5/5   | 5/5   | +0.00   |                                                                         |
| ord-orphaned-chunks   | ordinary    | pass  |    | pass  | 5/5   | 5/5   | +0.00   |                                                                         |
| ord-streaming-cost    | ordinary    | pass  |    | pass  | 5/5   | 5/5   | +0.00   |                                                                         |
| ord-three-buckets     | ordinary    | pass  |    | pass  | 5/5   | 5/5   | +0.00   |                                                                         |
| ord-two-timeouts      | ordinary    | pass  |    | pass  | 5/5   | 5/5   | +0.00   |                                                                         |
| kh-refund-window-meta | known_hard  | flaky | ^  | pass  | 4/5   | 5/5   | +0.20   | must_cite 4/5->5/5                                                      |

6 of 15 cases changed state. Unchanged rows are included on purpose: a comparison that prints only what moved cannot be checked against the one that did not.

## Per-bucket totals

| bucket      | A strict | Wilson A       | B strict | Wilson B       | b/c | McNemar p |
|-------------|----------|----------------|----------|----------------|-----|-----------|
| ordinary    | 4/4      | [0.510, 1.000] | 4/4      | [0.510, 1.000] | 0/0 | 1.0000    |
| known_hard  | 3/4      | [0.301, 0.954] | 4/4      | [0.510, 1.000] | 0/1 | 1.0000    |
| adversarial | 5/7      | [0.359, 0.918] | 1/7      | [0.026, 0.513] | 4/0 | 0.1250    |
| ALL         | 12/15    | [0.548, 0.930] | 9/15     | [0.357, 0.802] | 4/1 | 0.3750    |

b = passed under A and failed under B. c = the reverse. Concordant cases carry no information about the difference and are not in the test.

## Can you call it?

- discordant pairs: b=4 (A pass, B fail), c=1 (A fail, B pass)
- exact McNemar (exact_binomial): p = 0.3750
- paired bootstrap on per-case p-hat: delta = -0.3467, 95% CI [-0.573, -0.120] (B=10000, seed=20260817)
- A/A noise floor from 1000 random half-splits of A's own reruns: 95th percentile |delta| = 0.1000

**UNDERPOWERED, NOT NULL. Every one of the 5 discordant pair(s) went the same way, and with 5 the smallest two-sided p this test can produce is 0.0625. It cannot reach 0.05 however unanimous the evidence is, so p = 0.3750 here is a statement about the sample size and not about the prompt. The other two views do resolve it: the paired bootstrap [-0.573, -0.120] excludes zero, and the delta (-0.347) is 3.5x the A/A noise floor (0.100). Read the per-case table, then collect more cases before calling it significant. Do not report this as a null result.**

## Judge outcome, reported separately

| case                  | A    |    | B    |
|-----------------------|------|----|------|
| kh-chunk-size-trap    | pass | -> | pass |
| kh-refund-window-meta | pass | -> | pass |
| kh-refusal-dial       | pass | -> | pass |
| ord-streaming-cost    | pass | -> | pass |

4 case(s) judged on both sides. b=0, c=0, exact McNemar p = 1.0000 (smallest achievable at this discordance: 1.0000).

This is a second outcome, not a component of the first. Nothing above changes because of it. Folding a judge verdict into the pass/fail number would let a model's opinion gate a result the rubric says it may only flag, and it would do so without showing up anywhere a reader would look.

### What this comparison can and cannot detect

- cases: 15; discordance observed: 0.33
- minimum detectable effect at this n and discordance, exact test, 80% power: **no effect is detectable at all**. No delta reaches 80% power on this many cases, so the exact test is decorative here and the bootstrap plus the noise floor are the only views carrying information.
- smallest two-sided p the exact test can produce at 5 discordant pair(s): 0.0625

An effect smaller than the detectable minimum is not something this set can distinguish from noise, whatever the point estimate says. That is a property of the sample size, and it is printed here rather than left for the reader to work out, because the alternative is a report that implies it can bless a three-point improvement. The second line is the one people misread: when the smallest achievable p sits above 0.05, a non-significant result is not a finding about the prompt.
