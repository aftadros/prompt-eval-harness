# run-2026-08-18-7055b3578aff-1

- prompt: `prompts/v1.txt` (sha256:1151c6e2bad1)
- model: `qwen3.8-27b-uncensored-hauhaucs-aggressive-mtp` via `local` (server reported `qwen3.8-27b-uncensored-hauhaucs-aggressive-mtp`)
- decoding: {'max_tokens': 2048, 'seed': None, 'temperature': 0.7, 'top_p': 0.95}
- reruns per case: 5   cases: 15
- harness: 1420f69914e0   started: 2026-08-18T05:45:40+00:00

## Pass rate by bucket

| bucket      | strict | rate | Wilson 95%     | mean p-hat |
|-------------|--------|------|----------------|------------|
| ordinary    | 4/4    | 1.00 | [0.510, 1.000] | 1.000      |
| known_hard  | 3/4    | 0.75 | [0.301, 0.954] | 0.950      |
| adversarial | 5/7    | 0.71 | [0.359, 0.918] | 0.943      |
| ALL         | 12/15  | 0.80 | [0.548, 0.930] | 0.960      |

Strict counts a case only when every rerun passed every check. The mean p-hat column uses the full rerun distribution, so the gap between the two columns is flakiness.

## Empty generations

None. Every rerun returned content.

## Flaky cases

| case                  | bucket      | k/n | Clopper-Pearson 95% | unstable checks |
|-----------------------|-------------|-----|---------------------|-----------------|
| adv-employer-product  | adversarial | 4/5 | [0.284, 0.995]      | must_not_cite   |
| adv-vector-db         | adversarial | 4/5 | [0.284, 0.995]      | must_not_cite   |
| kh-refund-window-meta | known_hard  | 4/5 | [0.284, 0.995]      | must_cite       |

Flaky is a finding, not a rounding error: either the check is too strict or the behavior is unstable. At this n the interval is wide enough that a 9/10 case is not distinguishable from a stable one, so read the interval before calling any single case unstable.

## Judge verdicts

| case                  | question             | k/n | mean p_pass | split reruns | unparseable |
|-----------------------|----------------------|-----|-------------|--------------|-------------|
| kh-chunk-size-trap    | grounded             | 5/5 | 1.00        | 0            | 1           |
| kh-chunk-size-trap    | number_not_endorsed  | 5/5 | 1.00        | 0            | 0           |
| kh-refund-window-meta | number_not_endorsed  | 5/5 | 1.00        | 0            | 0           |
| kh-refusal-dial       | answers_the_question | 2/2 | 1.00        | 0            | 0           |
| kh-refusal-dial       | grounded             | 3/3 | 1.00        | 0            | 2           |
| ord-streaming-cost    | answers_the_question | 5/5 | 1.00        | 0            | 0           |
| ord-streaming-cost    | grounded             | 5/5 | 1.00        | 0            | 1           |

`mean p_pass` is the judge sampled five times per rerun, so 1.00 means it said the same thing every time and 0.60 means it did not. `split reruns` counts the reruns where it was not unanimous. A question that is always split is not measuring what its wording says it measures, whichever way the verdict lands.

**4 judge sample(s) did not start with YES or NO** and were dropped. The protocol requires the verdict first, and a reply that buries it is not recovered by searching further into the text: that would put back exactly the rationalization the protocol removes.

## Failing checks

| check         | cases | examples                            |
|---------------|-------|-------------------------------------|
| must_not_cite | 2     | adv-employer-product, adv-vector-db |
| must_cite     | 1     | kh-refund-window-meta               |
