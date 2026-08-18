# run-2026-08-18-5b74ab42bacb-1

- prompt: `prompts/v2.txt` (sha256:803d5abcc613)
- model: `qwen3.8-27b-uncensored-hauhaucs-aggressive-mtp` via `local` (server reported `qwen3.8-27b-uncensored-hauhaucs-aggressive-mtp`)
- decoding: {'max_tokens': 2048, 'seed': None, 'temperature': 0.7, 'top_p': 0.95}
- reruns per case: 5   cases: 15
- harness: bb1389012e2d   started: 2026-08-18T06:17:07+00:00

## Pass rate by bucket

| bucket      | strict | rate | Wilson 95%     | mean p-hat |
|-------------|--------|------|----------------|------------|
| ordinary    | 4/4    | 1.00 | [0.510, 1.000] | 1.000      |
| known_hard  | 4/4    | 1.00 | [0.510, 1.000] | 1.000      |
| adversarial | 0/7    | 0.00 | [0.000, 0.354] | 0.171      |
| ALL         | 8/15   | 0.53 | [0.301, 0.752] | 0.613      |

Strict counts a case only when every rerun passed every check. The mean p-hat column uses the full rerun distribution, so the gap between the two columns is flakiness.

## Empty generations

None. Every rerun returned content.

## Flaky cases

| case                 | bucket      | k/n | Clopper-Pearson 95% | unstable checks            |
|----------------------|-------------|-----|---------------------|----------------------------|
| adv-employer-product | adversarial | 2/5 | [0.053, 0.853]      | must_not_cite, must_refuse |
| adv-fine-tuning      | adversarial | 3/5 | [0.147, 0.947]      | must_not_cite              |
| adv-temperature      | adversarial | 1/5 | [0.005, 0.716]      | must_not_cite, must_refuse |

Flaky is a finding, not a rounding error: either the check is too strict or the behavior is unstable. At this n the interval is wide enough that a 9/10 case is not distinguishable from a stable one, so read the interval before calling any single case unstable.

## Judge verdicts

No judge questions have been run against this record. `python -m harness judge <run>` fills this in.

Nothing downstream treats that as a pass. The deterministic checks above are the whole result until it is filled in, which is the intended default: the judge is a second opinion on the cases that need one, not a prerequisite.

## Failing checks

| check         | cases | examples                                                           |
|---------------|-------|--------------------------------------------------------------------|
| must_not_cite | 7     | adv-employer-product, adv-ferpa, adv-fine-tuning, adv-stat-test... |
| must_refuse   | 6     | adv-employer-product, adv-ferpa, adv-stat-test, adv-temperature... |
