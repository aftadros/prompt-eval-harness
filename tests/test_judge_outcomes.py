"""Judge results as a second outcome, never folded into the first.

The rule the rubric states and this file enforces: a judge verdict may flag, not
gate. So the deterministic conjunction has to come out identical whether or not
any judging has happened, and the judge result has to be visible on its own
rather than absorbed into a number that looks deterministic.
"""

import pytest

from harness import judge as judge_mod
from harness import report
from harness.__main__ import build_flips, compare_stats
from tests.test_compare_and_report import make_record


def judge_rows(case_id, question_id, verdicts, p_pass=None):
    rows = []
    for i, v in enumerate(verdicts):
        rows.append({
            "case_id": case_id, "bucket": "known_hard", "rerun": i,
            "output_sha": f"sha256:{case_id}{i}", "question_id": question_id,
            "verdict": v, "p_pass": (p_pass[i] if p_pass else (1.0 if v == "pass" else 0.0)),
            "n_unparseable": 0,
        })
    return rows


def test_outcomes_counts_k_of_n_per_question():
    rec = {"judge": judge_rows("kh-x", "number_not_endorsed", ["pass", "pass", "fail"])}
    out = judge_mod.outcomes(rec)
    assert out["kh-x"]["number_not_endorsed"]["passes"] == 2
    assert out["kh-x"]["number_not_endorsed"]["n"] == 3


def test_outcomes_tracks_split_reruns_separately_from_verdicts():
    """5-0 and 3-2 both land on 'pass', and only one is worth acting on."""
    rec = {"judge": judge_rows("kh-x", "grounded", ["pass", "pass"], p_pass=[1.0, 0.6])}
    q = judge_mod.outcomes(rec)["kh-x"]["grounded"]
    assert q["passes"] == 2
    assert q["split"] == 1
    assert q["mean_p_pass"] == pytest.approx(0.8)


def test_outcomes_surfaces_unparseable_samples():
    rows = judge_rows("kh-x", "grounded", ["pass"])
    rows[0]["n_unparseable"] = 2
    assert judge_mod.outcomes({"judge": rows})["kh-x"]["grounded"]["unparseable"] == 2


@pytest.mark.parametrize(
    "verdicts,expected",
    [
        (["pass"] * 5, "pass"),
        (["fail"] * 5, "fail"),
        (["pass", "fail", "pass"], "flaky"),
        ([], "nodata"),
    ],
)
def test_case_judge_state(verdicts, expected):
    rec = {"judge": judge_rows("kh-x", "grounded", verdicts)}
    assert judge_mod.case_judge_state(judge_mod.outcomes(rec).get("kh-x", {})) == expected


def test_judge_never_changes_the_deterministic_result(tmp_path):
    """The load-bearing assertion. Same records, judged and unjudged, identical
    deterministic numbers."""
    a = make_record(tmp_path, "a", {"kh-x": ("known_hard", 5)})
    b = make_record(tmp_path, "b", {"kh-x": ("known_hard", 5)}, "prompts/v2.txt")
    plain = compare_stats(a, b, build_flips(a, b))

    a["judge"] = judge_rows("kh-x", "number_not_endorsed", ["pass"] * 5)
    b["judge"] = judge_rows("kh-x", "number_not_endorsed", ["fail"] * 5)
    judged = compare_stats(a, b, build_flips(a, b))

    assert judged["buckets"] == plain["buckets"]
    assert judged["bootstrap"] == plain["bootstrap"]
    assert judged["verdict"] == plain["verdict"]
    # ...and the judge regression is still reported, just somewhere else.
    assert judged["judge"]["b"] == 1 and judged["judge"]["c"] == 0


def test_judge_section_appears_in_the_comparison(tmp_path):
    a = make_record(tmp_path, "a", {"kh-x": ("known_hard", 5)})
    b = make_record(tmp_path, "b", {"kh-x": ("known_hard", 5)}, "prompts/v2.txt")
    a["judge"] = judge_rows("kh-x", "number_not_endorsed", ["pass"] * 5)
    b["judge"] = judge_rows("kh-x", "number_not_endorsed", ["fail"] * 5)
    flips = build_flips(a, b)
    md = report.compare_report(a, b, flips, compare_stats(a, b, flips))
    assert "Judge outcome, reported separately" in md
    assert "may only flag" in md


def test_unjudged_cases_are_excluded_from_the_judge_comparison(tmp_path):
    a = make_record(tmp_path, "a", {"kh-x": ("known_hard", 5), "ord-y": ("ordinary", 5)})
    b = make_record(tmp_path, "b", {"kh-x": ("known_hard", 5), "ord-y": ("ordinary", 5)})
    a["judge"] = judge_rows("kh-x", "grounded", ["pass"] * 5)
    b["judge"] = judge_rows("kh-x", "grounded", ["pass"] * 5)
    st = compare_stats(a, b, build_flips(a, b))
    assert st["judge"]["n"] == 1
    assert [c["case_id"] for c in st["judge"]["cases"]] == ["kh-x"]
