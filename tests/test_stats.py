"""Hand-rolled statistics against externally computed reference values.

Every reference value here was computed independently of this implementation and
the source is cited in the test that uses it. That citation is the whole point:
"we hand-rolled the statistics" is a claim, and a test asserting a function
against itself would not check it. These assertions are what makes the claim
inspectable by someone who does not trust the author.
"""

import math

import pytest

from harness import stats


# --- M1: Wilson score interval -------------------------------------------
# Reference: Wilson (1927), and the two anchors recorded in METRICS.md, which
# were computed with independent stdlib Python on 2026-07-27 before any of this
# code existed.


def test_wilson_matches_metrics_anchor_40_of_50():
    ci = stats.wilson(40, 50)
    assert round(ci.lo, 3) == 0.670
    assert round(ci.hi, 3) == 0.888


def test_wilson_matches_metrics_anchor_12_of_15():
    ci = stats.wilson(12, 15)
    assert round(ci.lo, 3) == 0.548
    assert round(ci.hi, 3) == 0.930


def test_wilson_does_not_collapse_at_the_boundary():
    """The reason Wilson is here instead of Wald.

    Wald gives [1.0, 1.0] for 15/15, which would print a perfect adversarial
    bucket as a certainty. Wilson keeps a lower bound below 1.
    """
    ci = stats.wilson(15, 15)
    assert ci.hi == 1.0
    assert 0.7 < ci.lo < 1.0


# --- M3: exact McNemar ----------------------------------------------------
# Reference: the two-sided binomial test against Bin(b+c, 1/2). Each value below
# is verifiable by hand from math.comb, and all six appear as power anchors in
# METRICS.md, computed independently on 2026-07-27.


@pytest.mark.parametrize(
    "b,c,expected",
    [
        (9, 1, 0.0215),   # 10 discordant, 9-1 split
        (8, 2, 0.1094),   # 10 discordant, 8-2 split
        (6, 0, 0.0312),   # 6 discordant, all one direction
        (7, 1, 0.0703),   # a single contrary flip costs you the result
        (12, 3, 0.0352),  # 15 inconsistent items, position-bias anchor
        (10, 2, 0.0386),  # 12 discordant, verbosity anchor
    ],
)
def test_mcnemar_exact_anchors(b, c, expected):
    assert round(stats.mcnemar_exact(b, c).p, 4) == expected


def test_mcnemar_hand_computed_from_binomial_coefficients():
    """2 * P(X <= 1) for X ~ Bin(10, 1/2) = 2 * (1 + 10) / 1024."""
    assert stats.mcnemar_exact(9, 1).p == pytest.approx(2 * (1 + 10) / 1024)


def test_mcnemar_is_symmetric_in_direction():
    assert stats.mcnemar_exact(9, 1).p == stats.mcnemar_exact(1, 9).p


def test_mcnemar_variant_switches_only_above_25_discordant():
    """The rule is in the code so the analyst cannot pick the flattering variant."""
    assert stats.mcnemar_exact(12, 12).variant == "exact_binomial"
    assert stats.mcnemar_exact(13, 12).variant == "chi2_continuity"


def test_mcnemar_no_discordant_pairs_is_p_one():
    assert stats.mcnemar_exact(0, 0).p == 1.0


# --- M4: paired bootstrap -------------------------------------------------


def test_bootstrap_is_deterministic_under_a_fixed_seed():
    a = [0.2, 0.4, 0.6, 0.8, 1.0] * 4
    b = [0.3, 0.5, 0.7, 0.9, 1.0] * 4
    first = stats.paired_bootstrap_delta(a, b, b_iters=500, seed=7)
    second = stats.paired_bootstrap_delta(a, b, b_iters=500, seed=7)
    assert first == second


def test_bootstrap_observed_delta_is_the_plain_mean_difference():
    a, b = [0.0, 0.5, 1.0], [0.5, 0.5, 1.0]
    observed, _ = stats.paired_bootstrap_delta(a, b, b_iters=200, seed=1)
    assert observed == pytest.approx(0.5 / 3)


def test_bootstrap_refuses_unequal_case_sets():
    with pytest.raises(ValueError):
        stats.paired_bootstrap_delta([0.1, 0.2], [0.1], b_iters=10)


def test_bootstrap_ci_brackets_the_observed_delta():
    a = [0.9] * 20 + [0.1] * 20
    b = [1.0] * 20 + [0.0] * 20
    observed, ci = stats.paired_bootstrap_delta(a, b, b_iters=2000, seed=3)
    assert ci.lo <= observed <= ci.hi


def test_percentile_interpolates():
    assert stats.percentile([0.0, 1.0], 50) == pytest.approx(0.5)
    assert stats.percentile([0.0, 10.0, 20.0], 100) == 20.0


# --- M6: kappa ------------------------------------------------------------
# Reference: Cohen (1960). The base-rate table below is METRICS.md's centerpiece
# and was computed independently on 2026-07-27.


@pytest.mark.parametrize(
    "pi,expected_pe,expected_kappa",
    [
        (0.50, 0.500, 0.600),
        (0.70, 0.580, 0.524),
        (0.80, 0.680, 0.375),
        (0.85, 0.745, 0.216),
        (0.90, 0.820, -0.111),
    ],
)
def test_kappa_implied_by_eighty_percent_raw_agreement(pi, expected_pe, expected_kappa):
    """The published rule of thumb, priced at each base rate.

    At a 90% pass rate, agreeing on four cases in five is worse than chance.
    """
    p_e, kappa = stats.kappa_at(0.80, pi)
    assert round(p_e, 3) == expected_pe
    assert round(kappa, 3) == expected_kappa


def test_kappa_of_perfect_agreement_is_one():
    j = [True, True, False, False]
    assert stats.cohens_kappa(j, j).kappa == pytest.approx(1.0)


def test_kappa_worked_example():
    """a=25 b=10 c=15 d=50: p_o = 0.75, p_e = 0.35*0.40 + 0.65*0.60 = 0.53,
    kappa = (0.75 - 0.53) / 0.47 = 0.46808..."""
    judge = [True] * 35 + [False] * 65
    human = [True] * 25 + [False] * 10 + [True] * 15 + [False] * 50
    ag = stats.cohens_kappa(judge, human)
    assert ag.confusion == {"a": 25, "b": 10, "c": 15, "d": 50}
    assert ag.raw == pytest.approx(0.75)
    assert ag.kappa == pytest.approx((0.75 - 0.53) / 0.47, abs=1e-9)
    assert ag.pabak == pytest.approx(0.5)


def test_kappa_rejects_mismatched_vectors():
    with pytest.raises(ValueError):
        stats.cohens_kappa([True], [True, False])


# --- M8: power ------------------------------------------------------------
# Reference: Connor, R.J. (1987), "Sample size for testing differences in
# proportions for the paired-sample design", Biometrics 43(1):207-211.


def test_connor_closed_form_matches_metrics_anchor():
    """psi = 0.2, delta = 0.16 -> n = 58.9, i.e. n=50 cannot see a 16-point move."""
    assert round(stats.connor_n(0.2, 0.16), 1) == 58.9


def test_connor_returns_infinity_when_the_effect_exceeds_discordance():
    assert stats.connor_n(0.1, 0.5) == float("inf")


def test_simulated_power_rises_with_sample_size():
    small = stats.mde_simulate(30, 0.2, 0.15, sims=600, seed=11)
    large = stats.mde_simulate(300, 0.2, 0.15, sims=600, seed=11)
    assert large > small


def test_simulated_power_at_zero_effect_is_near_alpha():
    """A test that rejects the null at nowhere near 5% when nothing is happening
    is a broken test, and this is the assertion that would catch it."""
    power = stats.mde_simulate(50, 0.2, 0.0, sims=3000, seed=5)
    assert power < 0.06


def test_symmetric_label_noise_costs_power():
    clean = stats.mde_simulate(200, 0.3, 0.15, sims=800, seed=9, label_noise=0.0)
    noisy = stats.mde_simulate(200, 0.3, 0.15, sims=800, seed=9, label_noise=0.3)
    assert noisy < clean


# --- M9: flakiness --------------------------------------------------------


def test_near_stable_cases_look_flaky_at_ten_reruns():
    """METRICS.md anchor: a p=0.95 case fails at least once in 10 runs 40% of the
    time, which is why the flaky classification is descriptive and not a test."""
    assert round(stats.prob_at_least_one_failure(0.95, 10), 4) == 0.4013


def test_flakiness_classification():
    f = stats.flakiness([[True] * 10, [False] * 10, [True] * 7 + [False] * 3])
    assert (f["stable_pass"], f["stable_fail"], f["flaky"]) == (1, 1, 1)
    assert f["flaky_share"] == pytest.approx(1 / 3)


def test_clopper_pearson_matches_published_interval():
    """9/10 -> [0.5550, 0.9975]. Reference: the standard exact binomial interval,
    tabulated in any statistics text and reproducible from the binomial tail."""
    ci = stats.clopper_pearson(9, 10)
    assert ci.lo == pytest.approx(0.5550, abs=5e-4)
    assert ci.hi == pytest.approx(0.9975, abs=5e-4)


def test_clopper_pearson_is_wider_than_wilson():
    exact, score = stats.clopper_pearson(8, 10), stats.wilson(8, 10)
    assert exact.lo < score.lo and exact.hi > score.hi


# --- M13 and corrections --------------------------------------------------


def test_fisher_exact_matches_reference_value():
    """Table [[8,2],[3,7]] gives two-sided p = 0.06978, a standard worked example."""
    assert stats.fisher_exact_2x2(8, 2, 3, 7) == pytest.approx(0.0698, abs=5e-4)


def test_fisher_of_a_null_table_is_one():
    assert stats.fisher_exact_2x2(5, 5, 5, 5) == pytest.approx(1.0)


def test_holm_rejects_only_below_the_stepped_threshold():
    """Reference: Holm (1979). With m=4 the smallest p is tested at 0.05/4."""
    out = stats.holm_bonferroni({"a": 0.01, "b": 0.02, "c": 0.03, "d": 0.9})
    assert out["a"]["threshold"] == pytest.approx(0.0125)
    assert out["a"]["rejected"] is True
    assert out["b"]["rejected"] is False  # 0.02 > 0.05/3
    assert out["c"]["rejected"] is False  # stops at the first failure
    assert out["d"]["rejected"] is False


def test_holm_adjusted_values_are_monotone():
    out = stats.holm_bonferroni({"a": 0.001, "b": 0.04, "c": 0.05, "d": 0.20})
    by_rank = sorted(out.values(), key=lambda v: v["rank"])
    adjusted = [v["adjusted"] for v in by_rank]
    assert adjusted == sorted(adjusted)


def test_holm_is_less_conservative_than_bonferroni():
    p = {"a": 0.02, "b": 0.03, "c": 0.04}
    out = stats.holm_bonferroni(p)
    assert out["a"]["threshold"] > 0.05 / 3 or out["a"]["threshold"] == pytest.approx(0.05 / 3)
    assert out["c"]["threshold"] == pytest.approx(0.05)


# --- M5: A/A noise floor --------------------------------------------------


def test_aa_floor_of_perfectly_stable_reruns_is_zero():
    """If every rerun agrees, half-splitting can never produce a difference."""
    floor = stats.aa_noise_floor([[True] * 10 for _ in range(20)], splits=100)
    assert floor["p95_mean_delta"] == 0.0


def test_aa_floor_is_positive_when_reruns_disagree():
    floor = stats.aa_noise_floor([[True, False] * 5 for _ in range(20)], splits=200)
    assert floor["p95_mean_delta"] > 0.0


def test_aa_floor_skips_cases_with_too_few_reruns():
    floor = stats.aa_noise_floor([[True], [False]], splits=10)
    assert floor["n_cases"] == 0


# --- functions the README claims are pinned ------------------------------
# These three are reachable from production paths (the position probe, the
# compare command, and calibrate respectively) and were untested when the README
# first claimed every function was covered. The claim is now true.


def test_binom_tail_two_sided_hand_computed():
    """P(X <= 1) doubled for X ~ Bin(5, 1/2) = 2 * (1 + 5) / 32 = 0.375."""
    assert stats.binom_tail_two_sided(1, 5) == pytest.approx(2 * 6 / 32)


def test_binom_tail_two_sided_is_one_at_the_center():
    assert stats.binom_tail_two_sided(5, 10) == 1.0


def test_binom_tail_two_sided_folds_to_the_smaller_tail():
    """k and n-k are the same test: the probe does not care which slot won."""
    assert stats.binom_tail_two_sided(2, 10) == stats.binom_tail_two_sided(8, 10)


def test_binom_tail_of_a_unanimous_split():
    """6 discordant, all one direction: 2 / 64 = 0.03125, the METRICS anchor."""
    assert stats.binom_tail_two_sided(0, 6) == pytest.approx(0.03125)


def test_find_mde_returns_a_detectable_effect():
    mde = stats.find_mde(50, 0.3, sims=400)
    assert 0 < mde <= 0.3
    assert stats.mde_simulate(50, 0.3, mde, sims=1500, seed=stats.DEFAULT_SEED) >= 0.75


def test_find_mde_shrinks_as_the_sample_grows():
    """The whole point of printing it: a bigger set resolves a smaller effect."""
    small = stats.find_mde(40, 0.3, sims=300)
    large = stats.find_mde(400, 0.3, sims=300)
    assert large < small


def test_find_mde_is_nan_when_no_effect_reaches_power():
    assert math.isnan(stats.find_mde(3, 0.05, sims=100))


def test_kappa_bootstrap_ci_brackets_the_point_estimate():
    judge = [True] * 35 + [False] * 65
    human = [True] * 25 + [False] * 10 + [True] * 15 + [False] * 50
    point = stats.cohens_kappa(judge, human).kappa
    ci = stats.kappa_bootstrap_ci(judge, human, b_iters=1500, seed=4)
    assert ci.lo <= point <= ci.hi


def test_kappa_bootstrap_ci_is_deterministic_under_a_seed():
    j, h = [True, False] * 20, [True, True, False, False] * 10
    assert stats.kappa_bootstrap_ci(j, h, b_iters=300, seed=2) == stats.kappa_bootstrap_ci(
        j, h, b_iters=300, seed=2
    )


def test_kappa_bootstrap_ci_of_an_empty_set_is_degenerate():
    ci = stats.kappa_bootstrap_ci([], [])
    assert (ci.lo, ci.hi) == (0.0, 0.0)


def test_every_public_stats_function_is_referenced_by_a_test():
    """Guard on the README's claim, so it cannot quietly go stale.

    A function added to stats.py without a test fails this, which is the only
    way a claim like "every function is pinned" survives contact with time.
    """
    import inspect
    import pathlib

    public = {
        name
        for name, obj in vars(stats).items()
        if inspect.isfunction(obj)
        and not name.startswith("_")
        and obj.__module__ == "harness.stats"
    }
    suite = "\n".join(
        p.read_text() for p in pathlib.Path(__file__).parent.glob("test_*.py")
    )
    # A call, not a mention: `stats.name(` so a comment cannot satisfy the guard.
    missing = sorted(n for n in public if f"stats.{n}(" not in suite)
    assert not missing, f"stats.py functions with no test: {missing}"


# --- the achievable-p floor ----------------------------------------------
# The number that separates "no effect" from "no power". With b+c discordant
# pairs the most extreme available result is all one direction, so the smallest
# two-sided p is 2 / 2**(b+c).


@pytest.mark.parametrize(
    "discordant,expected",
    [(2, 0.5000), (4, 0.1250), (5, 0.0625), (6, 0.0312), (10, 0.0020)],
)
def test_min_achievable_p(discordant, expected):
    assert round(stats.min_achievable_p(discordant), 4) == expected


def test_six_discordant_pairs_is_where_significance_becomes_possible():
    """Below six, no unanimous result can reach alpha = 0.05, however lopsided.

    This is the same fact METRICS.md records from the other side: six discordant
    all one direction gives p = 0.031, and a single contrary flip in eight pushes
    it back to 0.070. A report that prints p without this invites a null-result
    reading the data cannot support.
    """
    assert stats.min_achievable_p(4) == pytest.approx(0.125)
    assert stats.min_achievable_p(5) == pytest.approx(0.0625)
    assert stats.min_achievable_p(5) > 0.05
    assert stats.min_achievable_p(6) <= 0.05
    assert stats.min_achievable_p(6) == pytest.approx(stats.mcnemar_exact(6, 0).p)


def test_the_floor_equals_a_unanimous_exact_test():
    """The floor is not an approximation: it is what mcnemar_exact returns when
    every discordant pair goes one way."""
    for d in (3, 4, 6, 9):
        assert stats.min_achievable_p(d) == pytest.approx(stats.mcnemar_exact(d, 0).p)


def test_no_discordant_pairs_has_no_floor_below_one():
    assert stats.min_achievable_p(0) == 1.0


def test_aa_floor_estimates_a_twin_run_at_the_arms_own_n():
    """A half-split compares N//2 reruns against N//2 while the A/B it stands in
    for compares N against N. Unscaled, the split floor runs hot by sqrt(N/h):
    the reviewer measured 1.67x at N=5. Scaled by sqrt(h/N), the floor's 95th
    percentile has to sit on the 95th percentile of |delta| between two
    independent full-N arms drawn from the same per-case rates. Simulated here
    with a fixed seed; the tolerance is loose because both sides are sampled."""
    import random
    rng = random.Random(7)
    n_cases, n_reruns = 50, 5
    ps = [rng.choice([1.0, 1.0, 0.0, 0.8, 0.6, 0.4]) for _ in range(n_cases)]

    def arm():
        return [[rng.random() < p for _ in range(n_reruns)] for p in ps]

    floors = [stats.aa_noise_floor(arm(), splits=400, seed=i)["p95_mean_delta"] for i in range(6)]
    floor = sum(floors) / len(floors)
    twins = []
    for _ in range(1000):
        x, y = arm(), arm()
        twins.append(abs(sum(sum(b) / n_reruns - sum(a) / n_reruns for a, b in zip(x, y)) / n_cases))
    twin95 = stats.percentile(sorted(twins), 95)
    assert 0.8 < floor / twin95 < 1.2, (floor, twin95)


def test_kappa_is_undefined_when_both_raters_use_one_class():
    """Perfect agreement on an all-pass table is 0/0, not 'no better than chance'.
    statsmodels returns nan here; so do we, and the bootstrap skips resamples
    that collapse to one class instead of scoring them 0.0."""
    import math
    assert math.isnan(stats.cohens_kappa([True] * 6, [True] * 6).kappa)
    j = h = [True] * 15 + [False] * 3
    ci = stats.kappa_bootstrap_ci(j, h, b_iters=600, seed=3)
    assert ci.lo > 0.9, ci  # perfect agreement must not bootstrap down to [0, 1]
