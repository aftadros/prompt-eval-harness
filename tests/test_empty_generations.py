"""Empty completions are missing data, not failed checks.

This is the defect this file exists for, found by reading raw outputs during a
real collection rather than by reasoning about the code: three of five reruns for
one adversarial case came back with an empty body, because the model spent its
whole token budget on reasoning tokens that the server strips from `content`.

Scored naively that is worse than useless. An empty string fails `must_refuse`
and passes `must_not_cite` and `must_not_contain` vacuously, so a rig condition
arrives on the report as a refusal regression with two corroborating green checks
beside it. That is the precise false signal the harness was built to prevent, and
it would have been believed.
"""

import json
from unittest import mock

import pytest

from harness import model as model_mod
from harness import report
from harness.cases import load_all
from harness.runner import case_state, run_checks


def completion(text):
    return model_mod.Completion(text=text, model_reported="m", usage=None, raw={})


def test_an_empty_output_looks_like_a_refusal_regression():
    """The premise, asserted so nobody removes the guard as unnecessary."""
    case = next(c for c in load_all() if c.id == "adv-token-rates")
    results = {r.name.split(":")[0]: r.passed for r in run_checks("", case)}
    assert results["must_refuse"] is False
    assert results["must_not_cite"] is True
    assert results["must_not_contain"] is True


def test_is_empty_covers_whitespace_only():
    assert completion("").is_empty
    assert completion("   \n\t ").is_empty
    assert not completion("I can't answer that.").is_empty


def test_complete_with_content_retries_an_empty_body():
    calls = {"n": 0}

    class M:
        def complete(self, system, user, decoding):
            calls["n"] += 1
            return completion("" if calls["n"] < 3 else "real answer")

    got = model_mod.complete_with_content(M(), "s", "u", model_mod.Decoding())
    assert got.text == "real answer"
    assert calls["n"] == 3


def test_complete_with_content_gives_up_and_returns_the_empty_one():
    """It does not raise. The caller records missing data, which is a different
    thing from a run that could not proceed."""

    class M:
        def complete(self, system, user, decoding):
            return completion("")

    got = model_mod.complete_with_content(M(), "s", "u", model_mod.Decoding())
    assert got.is_empty


def test_a_case_with_no_usable_rerun_is_nodata_not_fail():
    """A broken rig and a broken prompt must not render identically."""
    assert case_state({"conjunction": {"passes": 0, "n": 0}, "empty": 5}) == "nodata"
    assert case_state({"conjunction": {"passes": 0, "n": 5}}) == "fail"


def test_partial_empties_shrink_n_rather_than_counting_as_failures():
    entry = {"conjunction": {"passes": 2, "n": 2}, "empty": 3}
    assert case_state(entry) == "pass"


def test_run_report_names_the_empty_count(tmp_path):
    from tests.test_compare_and_report import make_record

    rec = make_record(tmp_path, "r", {"c1": ("ordinary", 5)})
    rec["summary"]["c1"]["empty"] = 3
    md = report.run_report(rec)
    assert "## Empty generations" in md
    assert "came back empty" in md
    assert "dropping data quietly is its own dishonesty" in md


def test_run_report_says_none_when_there_are_none(tmp_path):
    from tests.test_compare_and_report import make_record

    rec = make_record(tmp_path, "r", {"c1": ("ordinary", 5)})
    assert "Every rerun returned content." in report.run_report(rec)


def test_compare_excludes_unpairable_cases_and_names_them(tmp_path):
    from harness.__main__ import build_flips, compare_stats
    from tests.test_compare_and_report import make_record

    a = make_record(tmp_path, "a", {"c1": ("ordinary", 5), "c2": ("ordinary", 5)})
    b = make_record(tmp_path, "b", {"c1": ("ordinary", 3), "c2": ("ordinary", 0)})
    b["summary"]["c2"]["conjunction"] = {"passes": 0, "n": 0}
    b["summary"]["c2"]["empty"] = 5

    flips = build_flips(a, b)
    assert [f["case_id"] for f in flips] == ["c1"]
    st = compare_stats(a, b, flips)
    assert st["unpairable_cases"] == ["c2"]
    md = report.compare_report(a, b, flips, st)
    assert "excluded as unpairable" in md
    assert "c2" in md
