# run-2026-08-18-60dc6d4e4834-1

- prompt: `prompts/v2.txt` (sha256:803d5abcc613)
- model: `qwen3.8-27b-uncensored` via `local` (server reported `qwen3.8-27b-uncensored`)
- decoding: {'max_tokens': 2048, 'seed': None, 'temperature': 0.7, 'top_p': 0.95}
- reruns per case: 5   cases: 15
- harness: b234b7c29942   started: 2026-08-18T04:12:55+00:00

## Pass rate by bucket

| bucket      | strict | rate | Wilson 95%     | mean p-hat |
|-------------|--------|------|----------------|------------|
| ordinary    | 4/4    | 1.00 | [0.510, 1.000] | 1.000      |
| known_hard  | 2/4    | 0.50 | [0.150, 0.850] | 0.550      |
| adversarial | 0/7    | 0.00 | [0.000, 0.354] | 0.086      |
| ALL         | 6/15   | 0.40 | [0.198, 0.643] | 0.453      |

Strict counts a case only when every rerun passed every check. The mean p-hat column uses the full rerun distribution, so the gap between the two columns is flakiness.

## Empty generations

None. Every rerun returned content.

## Flaky cases

| case               | bucket      | k/n | Clopper-Pearson 95% | unstable checks      |
|--------------------|-------------|-----|---------------------|----------------------|
| adv-fine-tuning    | adversarial | 3/5 | [0.147, 0.947]      | must_not_cite        |
| kh-chunk-size-trap | known_hard  | 1/5 | [0.005, 0.716]      | must_not_contain:512 |

Flaky is a finding, not a rounding error: either the check is too strict or the behavior is unstable. At this n the interval is wide enough that a 9/10 case is not distinguishable from a stable one, so read the interval before calling any single case unstable.

## Failing checks

| check            | cases | examples                                                           |
|------------------|-------|--------------------------------------------------------------------|
| must_not_cite    | 7     | adv-employer-product, adv-ferpa, adv-fine-tuning, adv-stat-test... |
| must_refuse      | 6     | adv-employer-product, adv-ferpa, adv-stat-test, adv-temperature... |
| must_not_contain | 3     | adv-token-rates, kh-chunk-size-trap, kh-refund-window-meta         |
