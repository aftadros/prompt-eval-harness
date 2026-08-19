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


class _ScrambledFakeJudge:
    """Deterministic verdicts, nondeterministic finish order.

    Each call answers YES or NO from a hash of the prompt, so the verdict for a
    given (output, question) never depends on timing, while a small hash-derived
    sleep makes later items routinely finish before earlier ones under a pool.
    """

    model = "fake-judge"

    def __init__(self):
        import threading
        self.calls = 0
        self._lock = threading.Lock()

    def preflight(self):
        return self.model

    def complete(self, system, user, decoding):
        import hashlib
        import time

        from harness.model import Completion
        h = hashlib.sha256(user.encode()).hexdigest()
        time.sleep((int(h[:2], 16) % 7) / 1000)
        with self._lock:
            self.calls += 1
        text = "YES because." if int(h[-1], 16) % 2 else "NO because."
        return Completion(text=text, model_reported=self.model, usage=None, raw={})


def _judge_run(tmp_path, name, case_id="ord-streaming-cost", n=4):
    """A run record holding outputs for one judge-routed case."""
    import json
    d = tmp_path / name
    (d / "outputs" / case_id).mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps({"n_cases": 1, "n_reruns": n}))
    with open(d / "results.jsonl", "w") as fh:
        for r in range(n):
            (d / "outputs" / case_id / f"r{r}.txt").write_text(f"answer number {r}\n")
            fh.write(json.dumps({"case_id": case_id, "bucket": "ordinary", "rerun": r,
                                 "output_sha": f"sha256:{case_id}{r}", "all_passed": True}) + "\n")
    return str(d)


def test_judge_concurrency_is_wall_clock_only(tmp_path, monkeypatch):
    """judge.jsonl at concurrency 4 is byte-identical to concurrency 1: same rows,
    same order, however the pool happened to finish them."""
    import os
    fake = _ScrambledFakeJudge()
    monkeypatch.setattr(judge_mod.model_mod, "build", lambda name, config=None: fake)

    serial = _judge_run(tmp_path, "serial")
    judge_mod.run_judge(serial, samples=3, quiet=True, concurrency=1)
    pooled = _judge_run(tmp_path, "pooled")
    judge_mod.run_judge(pooled, samples=3, quiet=True, concurrency=4)

    a = open(os.path.join(serial, "judge.jsonl")).read()
    b = open(os.path.join(pooled, "judge.jsonl")).read()
    assert a == b
    assert a.count("\n") == 4 * 2  # four reruns, two judge questions on this case
    # Both verdicts appear, so the equality above is not an artefact of a
    # constant fake.
    assert '"verdict":"pass"' in a and '"verdict":"fail"' in a


def test_judge_resumes_under_concurrency(tmp_path, monkeypatch):
    """A second pass skips every (case, rerun, question) already on disk, at any
    concurrency, and makes no model calls for them."""
    import os
    fake = _ScrambledFakeJudge()
    monkeypatch.setattr(judge_mod.model_mod, "build", lambda name, config=None: fake)
    run = _judge_run(tmp_path, "resume")
    first = judge_mod.run_judge(run, samples=2, quiet=True, concurrency=3)
    calls_after_first = fake.calls
    second = judge_mod.run_judge(run, samples=2, quiet=True, concurrency=3)
    assert len(first) == 8 and second == []
    assert fake.calls == calls_after_first
    assert open(os.path.join(run, "judge.jsonl")).read().count("\n") == 8


class _ScriptedJudge:
    """Returns the given texts in order, cycling; counts calls."""

    model = "scripted-judge"

    def __init__(self, texts):
        self.texts, self.i, self.calls = texts, 0, 0

    def preflight(self):
        return self.model

    def complete(self, system, user, decoding):
        from harness.model import Completion
        t = self.texts[self.i % len(self.texts)]
        self.i += 1
        self.calls += 1
        return Completion(text=t, model_reported=self.model, usage=None, raw={})


def _q(pass_when="no"):
    return {"id": "grounded", "question": "q?", "pass_when": pass_when}


def test_one_readable_sample_does_not_decide_a_verdict():
    """4 unparseable + 1 NO used to score pass, p_pass 1.0, no split: it read as
    unanimous. Below a readable majority the row is 'unparseable', and
    outcomes() counts it without scoring it."""
    j = _ScriptedJudge(["garbage", "garbage", "NO.", "garbage", "garbage"])
    v = judge_mod.judge_one(j, "{source}{question_input}{answer}{question}", _q(),
                            source="s", question_input="i", answer="a", samples=5)
    assert v["verdict"] == "unparseable" and v["n_unparseable"] == 4
    per = judge_mod.outcomes({"judge": [{"case_id": "c", "question_id": "grounded",
                                          "verdict": "unparseable", "p_pass": 1.0,
                                          "n_unparseable": 4}]})
    assert per["c"]["grounded"]["n"] == 0 and per["c"]["grounded"]["unparseable_rows"] == 1
    assert judge_mod.case_judge_state(per["c"]) == "nodata"


def test_all_unparseable_is_not_a_fail():
    j = _ScriptedJudge(["", "", "", "", ""])
    v = judge_mod.judge_one(j, "{source}{question_input}{answer}{question}", _q(),
                            source="s", question_input="i", answer="a", samples=5)
    assert v["verdict"] == "unparseable"


def test_three_readable_of_five_still_scores():
    j = _ScriptedJudge(["NO.", "NO.", "garbage", "NO.", "garbage"])
    v = judge_mod.judge_one(j, "{source}{question_input}{answer}{question}", _q(),
                            source="s", question_input="i", answer="a", samples=5)
    assert v["verdict"] == "pass" and v["n_unparseable"] == 2


def test_empty_judge_replies_are_retried():
    """An empty reply is the judge out of budget, not a verdict; it gets the same
    bounded retry the runner gives an empty generation."""
    from harness import model as model_mod
    j = _ScriptedJudge(["", "NO."])
    v = judge_mod.judge_one(j, "{source}{question_input}{answer}{question}", _q(),
                            source="s", question_input="i", answer="a", samples=1)
    assert v["samples"] == ["NO"] and j.calls == 2
    assert j.calls <= model_mod.MAX_ATTEMPTS * 1


def test_run_judge_skips_empty_answers(tmp_path, monkeypatch):
    """A rerun the runner recorded as empty carries all_passed None on the
    deterministic side; the judge must not manufacture a verdict for it."""
    import json
    import os
    fake = _ScrambledFakeJudge()
    monkeypatch.setattr(judge_mod.model_mod, "build", lambda name, config=None: fake)
    run = _judge_run(tmp_path, "empties", n=3)
    rows = [json.loads(l) for l in open(os.path.join(run, "results.jsonl"))]
    rows[1]["empty"] = True
    rows[1]["all_passed"] = None
    with open(os.path.join(run, "results.jsonl"), "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    written = judge_mod.run_judge(run, samples=1, quiet=True)
    assert {r["rerun"] for r in written} == {0, 2}
