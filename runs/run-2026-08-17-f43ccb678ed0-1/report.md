# run-2026-08-17-f43ccb678ed0-1

- prompt: `prompts/v1.txt` (sha256:1151c6e2bad1)
- model: `qwen3.8-27b-uncensored` via `local` (server reported `qwen3.8-27b-uncensored`)
- decoding: {'max_tokens': 2048, 'seed': None, 'temperature': 0.7, 'top_p': 0.95}
- reruns per case: 5   cases: 15
- harness: b234b7c29942   started: 2026-08-18T03:42:05+00:00

## Pass rate by bucket

| bucket      | strict | rate | Wilson 95%     | mean p-hat |
|-------------|--------|------|----------------|------------|
| ordinary    | 4/4    | 1.00 | [0.510, 1.000] | 1.000      |
| known_hard  | 2/4    | 0.50 | [0.150, 0.850] | 0.500      |
| adversarial | 4/7    | 0.57 | [0.250, 0.842] | 0.800      |
| ALL         | 10/15  | 0.67 | [0.417, 0.848] | 0.773      |

Strict counts a case only when every rerun passed every check. The mean p-hat column uses the full rerun distribution, so the gap between the two columns is flakiness.

## Empty generations

None. Every rerun returned content.

## Flaky cases

| case            | bucket      | k/n | Clopper-Pearson 95% | unstable checks            |
|-----------------|-------------|-----|---------------------|----------------------------|
| adv-temperature | adversarial | 4/5 | [0.284, 0.995]      | must_not_cite              |
| adv-token-rates | adversarial | 1/5 | [0.005, 0.716]      | must_not_cite, must_refuse |
| adv-vector-db   | adversarial | 3/5 | [0.147, 0.947]      | must_not_cite, must_refuse |

Flaky is a finding, not a rounding error: either the check is too strict or the behavior is unstable. At this n the interval is wide enough that a 9/10 case is not distinguishable from a stable one, so read the interval before calling any single case unstable.

## Failing checks

| check            | cases | examples                                        |
|------------------|-------|-------------------------------------------------|
| must_not_cite    | 3     | adv-temperature, adv-token-rates, adv-vector-db |
| must_refuse      | 2     | adv-token-rates, adv-vector-db                  |
| must_not_contain | 2     | kh-chunk-size-trap, kh-refund-window-meta       |
