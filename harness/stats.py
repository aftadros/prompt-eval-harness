"""Statistics, hand-rolled on the standard library.

Everything here reduces to arithmetic the stdlib already covers: exact McNemar is
a two-sided binomial test via `math.comb`, the paired bootstrap is
`random.Random(seed).choices` plus percentiles, and Wilson, kappa, Holm and the
rest are formulas. Importing scipy to sum binomial coefficients would contradict
the one architectural rule this repo has, and hand-rolled-with-tests is a
stronger claim than imported-and-hoped: `tests/test_stats.py` pins every function
against reference values computed independently and cited in the test.

The cost of skipping scipy is the exact-test variants: mid-p McNemar and BCa
bootstrap intervals are not here. That is a stated v2 line rather than silent
drift, and each function below names the variant it implements so there is never
a question about which one produced a number.

The functions do not decide anything. Deciding is `report.py`'s job, and the
separation matters: a p-value that knows what it is being used to argue for is a
p-value that will eventually be the flattering variant.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import NormalDist

Z95 = NormalDist().inv_cdf(0.975)
DEFAULT_B = 10_000
DEFAULT_SEED = 20260817


@dataclass(frozen=True)
class Interval:
    lo: float
    hi: float

    def __str__(self) -> str:
        return f"[{self.lo:.3f}, {self.hi:.3f}]"


# --------------------------------------------------------------------- M1


def wilson(x: int, n: int, z: float = Z95) -> Interval:
    """Wilson score interval for a binomial proportion.

    Wilson rather than Wald because Wald collapses to zero width at p = 0 and
    p = 1, which is guaranteed to happen in the adversarial bucket and would
    print "[1.000, 1.000]" for 15 out of 15. Wilson rather than bootstrap
    because a plain proportion over independent cases has a closed form and the
    bootstrap adds nothing; resampling is reserved for the rerun-nested
    quantities where it earns its keep.
    """
    if n == 0:
        return Interval(0.0, 1.0)
    p = x / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return Interval(max(0.0, center - half), min(1.0, center + half))


# --------------------------------------------------------------------- M3


def binom_tail_two_sided(k: int, n: int) -> float:
    """Two-sided binomial test of k against Bin(n, 1/2): double the min tail."""
    if n == 0:
        return 1.0
    k = min(k, n - k)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2**n)
    return min(1.0, 2 * tail)


def min_achievable_p(discordant: int) -> float:
    """The smallest two-sided p the exact test can produce at this discordance.

    With b+c discordant pairs the most extreme result available is all of them in
    one direction, which gives 2 / 2**(b+c). At four discordant pairs that floor
    is 0.125, so the test cannot reach alpha = 0.05 no matter how unanimous the
    evidence is.

    This is the number that separates "no effect" from "no power", and it is the
    single most useful thing a small paired comparison can print about itself. A
    report that shows p = 0.125 and stops invites the reader to conclude nothing
    happened, when the truth is that nothing *could* have registered.
    """
    if discordant <= 0:
        return 1.0
    return min(1.0, 2 / (2**discordant))


@dataclass(frozen=True)
class McNemar:
    b: int  # A passed, B failed
    c: int  # A failed, B passed
    p: float
    variant: str

    @property
    def discordant(self) -> int:
        return self.b + self.c


def mcnemar_exact(b: int, c: int, force_variant: str | None = None) -> McNemar:
    """Exact by default; chi-square with continuity correction only at b+c >= 25.

    The threshold is in the code rather than in the analyst's judgment on the
    day. At n = 50 cases the discordant count essentially never reaches 25, so
    the exact test is what runs, and stating the rule here means the code can
    never quietly pick whichever variant gave the nicer number.

    Concordant pairs carry no information about the difference and do not appear
    in the formula. The unpaired two-proportion z-test throws the pairing away
    and is not implemented anywhere in this repo on purpose.
    """
    n = b + c
    variant = force_variant or ("exact_binomial" if n < 25 else "chi2_continuity")
    if n == 0:
        return McNemar(b, c, 1.0, variant)
    if variant == "exact_binomial":
        return McNemar(b, c, binom_tail_two_sided(min(b, c), n), variant)
    stat = (abs(b - c) - 1) ** 2 / n
    p = 2 * (1 - NormalDist().cdf(math.sqrt(stat)))
    return McNemar(b, c, min(1.0, p), variant)


# --------------------------------------------------------------------- M4


def paired_bootstrap_delta(
    per_case_a: list[float],
    per_case_b: list[float],
    b_iters: int = DEFAULT_B,
    seed: int = DEFAULT_SEED,
) -> tuple[float, Interval]:
    """Percentile CI on mean(B) - mean(A), resampling CASES with replacement.

    The resample unit is cases, never reruns. Reruns within a case are correlated
    because case difficulty dominates, so resampling reruns manufactures an n the
    data does not have and shrinks the interval dishonestly. This is the single
    easiest mistake to make in this file and the one that would be hardest to
    spot in a finished report, which is why the sentence is here and repeated in
    METRICS.md.
    """
    if len(per_case_a) != len(per_case_b):
        raise ValueError("paired bootstrap needs the same cases in both arms")
    n = len(per_case_a)
    if n == 0:
        return 0.0, Interval(0.0, 0.0)
    deltas = [per_case_b[i] - per_case_a[i] for i in range(n)]
    observed = sum(deltas) / n
    rng = random.Random(seed)
    idx = range(n)
    samples = []
    for _ in range(b_iters):
        pick = rng.choices(idx, k=n)
        samples.append(sum(deltas[i] for i in pick) / n)
    samples.sort()
    return observed, Interval(percentile(samples, 2.5), percentile(samples, 97.5))


def percentile(sorted_values: list[float], q: float) -> float:
    """Linear-interpolated percentile of an already-sorted list."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = (q / 100) * (len(sorted_values) - 1)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return sorted_values[int(pos)]
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)


# --------------------------------------------------------------------- M5


def aa_noise_floor(
    per_case_reruns: list[list[bool]],
    splits: int = 1000,
    seed: int = DEFAULT_SEED,
) -> dict:
    """Empirical noise floor: split one arm's reruns in half and compare halves.

    This is what "running the same prompt twice" actually looks like on this rig,
    measured rather than assumed. The parametric null says what a difference
    should look like under Bin(N, p); this says what it does look like when the
    server, the batching and the sampler are whatever they are. The 95th
    percentile of |delta| is the floor a real A/B delta has to clear.

    A half-split compares h reruns against h, where h = N // 2, while the A/B
    it stands in for compares N against N. The variance of a per-case mean
    difference goes as (1/h + 1/h) for the split and (1/N + 1/N) for the real
    pair, so an unscaled split floor runs hot by sqrt(N/h): about 1.6x at N=5
    and 1.4x at N=10. Each per-case split delta is scaled by sqrt(h/N) so the
    floor estimates a twin run at the arm's own N rather than at half of it.
    The vote delta is left unscaled; it is a count, not a mean.
    """
    rng = random.Random(seed)
    mean_deltas: list[float] = []
    vote_deltas: list[int] = []
    usable = [r for r in per_case_reruns if len(r) >= 2]
    if not usable:
        return {"splits": 0, "p95_mean_delta": 0.0, "p95_vote_delta": 0, "n_cases": 0}
    for _ in range(splits):
        md, vd = 0.0, 0
        for reruns in usable:
            shuffled = list(reruns)
            rng.shuffle(shuffled)
            half = len(shuffled) // 2
            left, right = shuffled[:half], shuffled[half : 2 * half]
            scale = math.sqrt(half / len(reruns))
            md += scale * ((sum(right) / len(right)) - (sum(left) / len(left)))
            lv = sum(left) * 2 > len(left)
            rv = sum(right) * 2 > len(right)
            vd += int(rv) - int(lv)
        mean_deltas.append(md / len(usable))
        vote_deltas.append(vd)
    abs_mean = sorted(abs(d) for d in mean_deltas)
    abs_vote = sorted(abs(d) for d in vote_deltas)
    return {
        "splits": splits,
        "n_cases": len(usable),
        "p95_mean_delta": percentile(abs_mean, 95),
        "p95_vote_delta": percentile([float(v) for v in abs_vote], 95),
        "max_mean_delta": abs_mean[-1] if abs_mean else 0.0,
    }


# --------------------------------------------------------------------- M6


@dataclass(frozen=True)
class Agreement:
    n: int
    raw: float
    kappa: float
    pabak: float
    confusion: dict[str, int]
    kappa_ci: Interval | None = None


def cohens_kappa(judge: list[bool], human: list[bool]) -> Agreement:
    """Raw agreement, Cohen's kappa, PABAK, and the 2x2 that produced them.

    Kappa is printed next to raw agreement rather than instead of it because the
    two come apart badly at skewed base rates. At a 90% pass rate, 80% raw
    agreement corresponds to kappa = -0.111: worse than chance, from a number
    that reads like a healthy result. PABAK is the balanced-marginals companion,
    so the gap between kappa and PABAK shows how much of the disagreement story
    is base rate rather than reliability.
    """
    if len(judge) != len(human):
        raise ValueError("judge and human label vectors must be the same length")
    n = len(judge)
    if n == 0:
        return Agreement(0, 0.0, 0.0, 0.0, {"a": 0, "b": 0, "c": 0, "d": 0})
    a = sum(1 for j, h in zip(judge, human, strict=True) if j and h)
    b = sum(1 for j, h in zip(judge, human, strict=True) if j and not h)
    c = sum(1 for j, h in zip(judge, human, strict=True) if not j and h)
    d = sum(1 for j, h in zip(judge, human, strict=True) if not j and not h)
    p_o = (a + d) / n
    pj, ph = (a + b) / n, (a + c) / n
    p_e = pj * ph + (1 - pj) * (1 - ph)
    # p_e == 1 means both raters used a single class, so chance agreement is
    # total and kappa is 0/0: undefined, not zero. Returning 0.0 here would
    # report "no better than chance" for a table that may be perfect agreement.
    kappa = float("nan") if p_e == 1 else (p_o - p_e) / (1 - p_e)
    return Agreement(n, p_o, kappa, 2 * p_o - 1, {"a": a, "b": b, "c": c, "d": d})


def kappa_bootstrap_ci(
    judge: list[bool], human: list[bool], b_iters: int = DEFAULT_B, seed: int = DEFAULT_SEED
) -> Interval:
    """Percentile CI on kappa, resampling labeled items."""
    n = len(judge)
    if n == 0:
        return Interval(0.0, 0.0)
    rng = random.Random(seed)
    out = []
    for _ in range(b_iters):
        pick = rng.choices(range(n), k=n)
        k = cohens_kappa([judge[i] for i in pick], [human[i] for i in pick]).kappa
        # A resample that drops every member of one class has no kappa. Keeping
        # it as 0.0 used to pull the interval of a perfect-agreement set down to
        # [0.0, 1.0]. Undefined resamples are skipped, not scored.
        if not math.isnan(k):
            out.append(k)
    if not out:
        return Interval(float("nan"), float("nan"))
    out.sort()
    return Interval(percentile(out, 2.5), percentile(out, 97.5))


def kappa_at(p_o: float, pi: float) -> tuple[float, float]:
    """What a given raw agreement implies at a given shared marginal pass rate.

    The engine behind the published-heuristic table: returns (p_e, kappa). This
    is what makes "we disagree on a fifth of cases" a statement whose meaning
    depends entirely on a number the rule of thumb never mentions.
    """
    p_e = pi * pi + (1 - pi) * (1 - pi)
    return p_e, (0.0 if p_e == 1 else (p_o - p_e) / (1 - p_e))


# --------------------------------------------------------------------- M8


def connor_n(psi: float, delta: float, alpha: float = 0.05, power: float = 0.80) -> float:
    """Connor (1987) closed form for a paired binary comparison.

    n = [z(1-a/2)*sqrt(psi) + z(power)*sqrt(psi - delta^2)]^2 / delta^2
    """
    if delta <= 0 or psi <= 0 or psi - delta**2 <= 0:
        return float("inf")
    za = NormalDist().inv_cdf(1 - alpha / 2)
    zb = NormalDist().inv_cdf(power)
    return (za * math.sqrt(psi) + zb * math.sqrt(psi - delta**2)) ** 2 / delta**2


def mde_simulate(
    n: int,
    psi: float,
    delta: float,
    sims: int = 5000,
    alpha: float = 0.05,
    seed: int = DEFAULT_SEED,
    label_noise: float = 0.0,
) -> float:
    """Power of the exact paired test at a given n, discordance and true effect.

    Simulation is primary and the closed form is the cross-check, not the other
    way round, because the closed form assumes away exactly the things that bite
    at n = 50: the discreteness of the exact test and the fact that with ten
    discordant pairs the achievable p-values are a short list rather than a
    continuum.

    `label_noise` flips outcomes symmetrically at the stated rate, which is the
    variance half of the fifty-clean-versus-five-hundred-lazy question.
    """
    if psi <= 0 or abs(delta) > psi:
        return 0.0
    rng = random.Random(seed)
    p_b_wins = (psi + delta) / 2
    rejections = 0
    for _ in range(sims):
        b = c = 0
        for _ in range(n):
            if rng.random() < psi:
                b_won = rng.random() < (p_b_wins / psi)
                if label_noise and rng.random() < label_noise:
                    b_won = not b_won
                if b_won:
                    c += 1
                else:
                    b += 1
        if mcnemar_exact(b, c).p <= alpha:
            rejections += 1
    return rejections / sims


def find_mde(
    n: int, psi: float, sims: int = 2000, target_power: float = 0.80, seed: int = DEFAULT_SEED
) -> float:
    """Smallest delta reaching target power, to two decimal places."""
    for step in range(1, int(psi * 100) + 1):
        delta = step / 100
        if mde_simulate(n, psi, delta, sims=sims, seed=seed) >= target_power:
            return delta
    return float("nan")


# --------------------------------------------------------------------- M9


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> Interval:
    """Exact binomial interval by bisection on the binomial tail.

    No incomplete beta function needed: at n = 10 the tail is a short sum of
    `math.comb` terms and bisection converges in fifty iterations.
    """
    if n == 0:
        return Interval(0.0, 1.0)

    def upper_tail(p: float, k_: int) -> float:
        return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k_, n + 1))

    def lower_tail(p: float, k_: int) -> float:
        return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(0, k_ + 1))

    lo = 0.0
    if k > 0:
        a, b = 0.0, 1.0
        for _ in range(200):
            mid = (a + b) / 2
            if upper_tail(mid, k) < alpha / 2:
                a = mid
            else:
                b = mid
        lo = (a + b) / 2
    hi = 1.0
    if k < n:
        a, b = 0.0, 1.0
        for _ in range(200):
            mid = (a + b) / 2
            if lower_tail(mid, k) > alpha / 2:
                a = mid
            else:
                b = mid
        hi = (a + b) / 2
    return Interval(lo, hi)


def flakiness(per_case_reruns: list[list[bool]]) -> dict:
    """Stable-pass / stable-fail / flaky, with the caveat that matters.

    "Flaky" at N = 10 includes near-stable cases: a case whose true pass
    probability is 0.95 shows at least one failure in ten runs 40% of the time.
    The classification is descriptive, never a test, and the per-case
    Clopper-Pearson interval is what a reader should look at before calling any
    single case unstable.
    """
    stable_pass = stable_fail = flaky = 0
    for reruns in per_case_reruns:
        n = len(reruns)
        k = sum(reruns)
        if n == 0:
            continue
        if k == n:
            stable_pass += 1
        elif k == 0:
            stable_fail += 1
        else:
            flaky += 1
    total = stable_pass + stable_fail + flaky
    return {
        "stable_pass": stable_pass,
        "stable_fail": stable_fail,
        "flaky": flaky,
        "total": total,
        "flaky_share": flaky / total if total else 0.0,
        "flaky_share_ci": wilson(flaky, total) if total else Interval(0.0, 1.0),
    }


def prob_at_least_one_failure(p: float, n: int) -> float:
    """P(at least one failure in n runs) for a case with true pass rate p."""
    return 1 - p**n


# -------------------------------------------------------------------- M11/M13


def fisher_exact_2x2(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact test by summing tables no more likely than observed."""
    n = a + b + c + d
    if n == 0:
        return 1.0
    row1, col1 = a + b, a + c

    def prob(x: int) -> float:
        return (
            math.comb(row1, x)
            * math.comb(n - row1, col1 - x)
            / math.comb(n, col1)
        )

    observed = prob(a)
    lo = max(0, col1 - (n - row1))
    hi = min(row1, col1)
    return min(1.0, sum(prob(x) for x in range(lo, hi + 1) if prob(x) <= observed + 1e-12))


# ---------------------------------------------------------------- corrections


def holm_bonferroni(p_values: dict[str, float], alpha: float = 0.05) -> dict[str, dict]:
    """Holm-Bonferroni over a family declared before any data was collected.

    Holm because familywise error is the right frame for ship / do-not-ship
    claims, it assumes nothing about independence, and it uniformly dominates
    Bonferroni. Not Benjamini-Hochberg: the family is small and each member is
    individually load-bearing, so controlling the false discovery *rate* across
    them would be controlling the wrong thing.

    House rule enforced by the caller, not here: only corrected p-values may use
    the word "significant".
    """
    items = sorted(p_values.items(), key=lambda kv: kv[1])
    m = len(items)
    out: dict[str, dict] = {}
    still_rejecting = True
    running_max = 0.0
    for i, (name, p) in enumerate(items):
        threshold = alpha / (m - i)
        if still_rejecting and p <= threshold:
            rejected = True
        else:
            rejected = False
            still_rejecting = False
        # Adjusted p-values are enforced monotone non-decreasing down the sorted
        # family, which is what makes them comparable to a flat alpha.
        running_max = max(running_max, min(1.0, p * (m - i)))
        out[name] = {
            "p": p,
            "rank": i + 1,
            "threshold": threshold,
            "rejected": rejected,
            "adjusted": running_max,
        }
    return out
