# run-2026-08-17-f43ccb678ed0-1  ->  run-2026-08-18-60dc6d4e4834-1

- A: `prompts/v1.txt` (sha256:1151c6e2bad1)
- B: `prompts/v2.txt` (sha256:803d5abcc613)
- model: `qwen3.8-27b-uncensored` -> `qwen3.8-27b-uncensored`
- reruns: 5 / 5   cases: 15

## Per-case changes, regressions first

| case                  | bucket      | A     |    | B     | k/n A | k/n B | d p-hat | checks flipped                                                          |
|-----------------------|-------------|-------|----|-------|-------|-------|---------|-------------------------------------------------------------------------|
| adv-employer-product  | adversarial | pass  | vv | fail  | 5/5   | 0/5   | -1.00   | must_not_cite 5/5->0/5, must_refuse 5/5->0/5                            |
| adv-ferpa             | adversarial | pass  | vv | fail  | 5/5   | 0/5   | -1.00   | must_not_cite 5/5->0/5, must_refuse 5/5->0/5                            |
| adv-stat-test         | adversarial | pass  | vv | fail  | 5/5   | 0/5   | -1.00   | must_not_cite 5/5->0/5, must_refuse 5/5->0/5                            |
| adv-temperature       | adversarial | flaky | v  | fail  | 4/5   | 0/5   | -0.80   | must_not_cite 4/5->0/5, must_refuse 5/5->0/5                            |
| adv-vector-db         | adversarial | flaky | v  | fail  | 3/5   | 0/5   | -0.60   | must_not_cite 3/5->0/5, must_refuse 4/5->0/5                            |
| adv-fine-tuning       | adversarial | pass  | v  | flaky | 5/5   | 3/5   | -0.40   | must_not_cite 5/5->3/5                                                  |
| adv-token-rates       | adversarial | flaky | v  | fail  | 1/5   | 0/5   | -0.20   | must_not_cite 1/5->0/5, must_not_contain 5/5->3/5, must_refuse 1/5->0/5 |
| kh-guardrail-down     | known_hard  | pass  |    | pass  | 5/5   | 5/5   | +0.00   |                                                                         |
| kh-refund-window-meta | known_hard  | fail  |    | fail  | 0/5   | 0/5   | +0.00   |                                                                         |
| kh-refusal-dial       | known_hard  | pass  |    | pass  | 5/5   | 5/5   | +0.00   |                                                                         |
| ord-orphaned-chunks   | ordinary    | pass  |    | pass  | 5/5   | 5/5   | +0.00   |                                                                         |
| ord-streaming-cost    | ordinary    | pass  |    | pass  | 5/5   | 5/5   | +0.00   |                                                                         |
| ord-three-buckets     | ordinary    | pass  |    | pass  | 5/5   | 5/5   | +0.00   |                                                                         |
| ord-two-timeouts      | ordinary    | pass  |    | pass  | 5/5   | 5/5   | +0.00   |                                                                         |
| kh-chunk-size-trap    | known_hard  | fail  | ^  | flaky | 0/5   | 1/5   | +0.20   | must_not_contain 0/5->1/5                                               |

8 of 15 cases changed state. Unchanged rows are included on purpose: a comparison that prints only what moved cannot be checked against the one that did not.

## Per-bucket totals

| bucket      | A strict | Wilson A       | B strict | Wilson B       | b/c | McNemar p |
|-------------|----------|----------------|----------|----------------|-----|-----------|
| ordinary    | 4/4      | [0.510, 1.000] | 4/4      | [0.510, 1.000] | 0/0 | 1.0000    |
| known_hard  | 2/4      | [0.150, 0.850] | 2/4      | [0.150, 0.850] | 0/0 | 1.0000    |
| adversarial | 4/7      | [0.250, 0.842] | 0/7      | [0.000, 0.354] | 4/0 | 0.1250    |
| ALL         | 10/15    | [0.417, 0.848] | 6/15     | [0.198, 0.643] | 4/0 | 0.1250    |

b = passed under A and failed under B. c = the reverse. Concordant cases carry no information about the difference and are not in the test.

## Can you call it?

- discordant pairs: b=4 (A pass, B fail), c=0 (A fail, B pass)
- exact McNemar (exact_binomial): p = 0.1250
- paired bootstrap on per-case p-hat: delta = -0.3200, 95% CI [-0.533, -0.107] (B=10000, seed=20260817)
- A/A noise floor from 1000 random half-splits of A's own reruns: 95th percentile |delta| = 0.1000

**UNDERPOWERED, NOT NULL. Every one of the 4 discordant pair(s) went the same way, and with 4 the smallest two-sided p this test can produce is 0.1250. It cannot reach 0.05 however unanimous the evidence is, so p = 0.1250 here is a statement about the sample size and not about the prompt. The other two views do resolve it: the paired bootstrap [-0.533, -0.107] excludes zero, and the delta (-0.320) is 3.2x the A/A noise floor (0.100). Read the per-case table, then collect more cases before calling it significant. Do not report this as a null result.**

### What this comparison can and cannot detect

- cases: 15; discordance observed: 0.27
- minimum detectable effect at this n and discordance, exact test, 80% power: **no effect is detectable at all**. No delta reaches 80% power on this many cases, so the exact test is decorative here and the bootstrap plus the noise floor are the only views carrying information.
- smallest two-sided p the exact test can produce at 4 discordant pair(s): 0.1250

An effect smaller than the detectable minimum is not something this set can distinguish from noise, whatever the point estimate says. That is a property of the sample size, and it is printed here rather than left for the reader to work out, because the alternative is a report that implies it can bless a three-point improvement. The second line is the one people misread: when the smallest achievable p sits above 0.05, a non-significant result is not a finding about the prompt.
