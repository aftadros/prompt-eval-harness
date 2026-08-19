"""The comparison path end to end, on constructed records and no model.

The scenario built here is the one the whole repo exists for: prompt B lifts the
ordinary bucket, regresses the adversarial bucket, and comes out flat or slightly
positive on the aggregate. If the report's headline were the average, that change
ships. The assertions below are that it does not.
"""

import json
import os
import re

import pytest

from harness import records, report
from harness.__main__ import build_flips, compare_stats


def make_record(tmp_path, name, states, prompt="prompts/v1.txt", n=5):
    """states: {case_id: (bucket, k_passes_out_of_n)}"""
    d = tmp_path / name
    (d / "outputs").mkdir(parents=True)
    manifest = {
        "prompt": {"path": prompt, "sha256": "sha256:" + "0" * 64},
        "cases": {"ordinary.yaml": "sha256:aaa"},
        "corpus": {"fixtures/x.md": "sha256:bbb"},
        "model": {"name": "local", "kind": "openai_compat", "base_url": "http://x",
                  "requested": "m", "server_reported": "m"},
        "decoding": {"temperature": 0.7}, "n_reruns": n, "n_cases": len(states),
        "harness_git_sha": "deadbeef" * 5, "python": "3.14.0", "started": "2026-08-17T00:00:00+00:00",
        "judge": None,
    }
    with open(d / "manifest.json", "w") as fh:
        json.dump(manifest, fh)
    summary, results = {}, []
    for cid, (bucket, k) in states.items():
        summary[cid] = {
            "bucket": bucket, "n": n,
            "checks": {"must_cite": {"passes": k, "n": n}},
            "judge_questions": [], "conjunction": {"passes": k, "n": n},
        }
        for r in range(n):
            results.append({"case_id": cid, "bucket": bucket, "rerun": r,
                            "output_sha": f"sha256:{cid}{r}", "all_passed": r < k})
    with open(d / "summary.json", "w") as fh:
        json.dump(summary, fh)
    with open(d / "results.jsonl", "w") as fh:
        for row in results:
            fh.write(json.dumps(row) + "\n")
    return records.load_record(str(d))


@pytest.fixture
def hidden_regression(tmp_path):
    """Six ordinary cases improve, six adversarial cases collapse."""
    a_states, b_states = {}, {}
    for i in range(6):
        a_states[f"ord-{i}"] = ("ordinary", 3)
        b_states[f"ord-{i}"] = ("ordinary", 5)
    for i in range(6):
        a_states[f"adv-{i}"] = ("adversarial", 5)
        b_states[f"adv-{i}"] = ("adversarial", 0)
    return make_record(tmp_path, "run-a", a_states), make_record(tmp_path, "run-b", b_states, "prompts/v2.txt")


def test_flips_are_three_valued(tmp_path):
    a = make_record(tmp_path, "a", {"c1": ("ordinary", 5), "c2": ("ordinary", 3), "c3": ("ordinary", 0)})
    b = make_record(tmp_path, "b", {"c1": ("ordinary", 3), "c2": ("ordinary", 5), "c3": ("ordinary", 0)})
    flips = {f["case_id"]: f for f in build_flips(a, b)}
    assert (flips["c1"]["state_a"], flips["c1"]["state_b"]) == ("pass", "flaky")
    assert (flips["c2"]["state_a"], flips["c2"]["state_b"]) == ("flaky", "pass")
    assert (flips["c3"]["state_a"], flips["c3"]["state_b"]) == ("fail", "fail")


def test_pass_to_flaky_is_visible_as_its_own_class(tmp_path):
    """A change that converts stable passes into flaky ones is a regression, and a
    two-valued outcome cannot express it."""
    a = make_record(tmp_path, "a", {"c1": ("ordinary", 5)})
    b = make_record(tmp_path, "b", {"c1": ("ordinary", 4)})
    f = build_flips(a, b)[0]
    assert f["state_a"] == "pass" and f["state_b"] == "flaky"
    assert f["delta"] == pytest.approx(-0.2)


def test_the_aggregate_hides_what_the_buckets_show(hidden_regression):
    a, b = hidden_regression
    flips = build_flips(a, b)
    st = compare_stats(a, b, flips)
    # Aggregate: 6 cases gained a strict pass, 6 lost one. Perfectly balanced.
    assert st["buckets"]["ALL"]["b"] == 6 and st["buckets"]["ALL"]["c"] == 6
    assert st["buckets"]["ALL"]["p"] == pytest.approx(1.0)
    # The adversarial bucket alone is unanimous and significant.
    assert st["buckets"]["adversarial"]["b"] == 6
    assert st["buckets"]["adversarial"]["c"] == 0
    assert st["buckets"]["adversarial"]["p"] == pytest.approx(0.03125)


def test_report_puts_regressions_at_the_top(hidden_regression):
    a, b = hidden_regression
    flips = build_flips(a, b)
    md = report.compare_report(a, b, flips, compare_stats(a, b, flips))
    body = md[md.index("## Per-case changes"):]
    first_adv = body.index("adv-")
    first_ord = body.index("ord-")
    assert first_adv < first_ord, "regressions must sort above improvements"


def test_report_prints_the_detectability_limit(hidden_regression):
    a, b = hidden_regression
    flips = build_flips(a, b)
    md = report.compare_report(a, b, flips, compare_stats(a, b, flips))
    assert "minimum detectable effect" in md
    assert "can and cannot detect" in md


def test_verdict_refuses_to_call_a_balanced_change(hidden_regression):
    a, b = hidden_regression
    flips = build_flips(a, b)
    st = compare_stats(a, b, flips)
    assert "Do not ship on this delta." in st["verdict"]


def test_verdict_names_absence_of_evidence_rather_than_evidence_of_absence(hidden_regression):
    a, b = hidden_regression
    st = compare_stats(a, b, build_flips(a, b))
    assert "not evidence of no effect" in st["verdict"] or "noise floor" in st["verdict"]


def test_compare_refuses_mismatched_case_sets(tmp_path, capsys):
    from harness.__main__ import cmd_compare

    a = make_record(tmp_path, "a", {"c1": ("ordinary", 5)})
    b = make_record(tmp_path, "b", {"c1": ("ordinary", 5)})
    with open(os.path.join(b["path"], "manifest.json")) as fh:
        m = json.load(fh)
    m["cases"] = {"ordinary.yaml": "sha256:DIFFERENT"}
    with open(os.path.join(b["path"], "manifest.json"), "w") as fh:
        json.dump(m, fh)

    class Args:
        run_a, run_b = a["path"], b["path"]

    assert cmd_compare(Args()) == 2
    assert "paired statistics require the same paired cases" in capsys.readouterr().err.lower()


def test_run_report_separates_strict_from_mean(tmp_path):
    rec = make_record(tmp_path, "r", {"c1": ("ordinary", 5), "c2": ("ordinary", 3)})
    md = report.run_report(rec)
    assert "1/2" in md          # strict: only one case passed every rerun
    assert "0.800" in md        # mean p-hat: (1.0 + 0.6) / 2
    assert "flakiness" in md


def test_run_report_lists_flaky_cases_with_intervals(tmp_path):
    rec = make_record(tmp_path, "r", {"c1": ("ordinary", 3)})
    md = report.run_report(rec)
    assert "## Flaky cases" in md
    assert "Clopper-Pearson" in md


def test_plain_text_rendering_keeps_the_tables(tmp_path):
    rec = make_record(tmp_path, "r", {"c1": ("ordinary", 5)})
    plain = report.to_plain(report.run_report(rec))
    assert "**" not in plain
    assert "|" in plain


def test_underpowered_verdict_refuses_a_null_reading(tmp_path):
    """Four discordant pairs, all one direction: a real effect the exact test
    structurally cannot certify. The verdict has to say which of those two things
    it is, because 'p = 0.125' alone reads as 'nothing happened'."""
    from harness.__main__ import build_flips, compare_stats

    a_states = {f"adv-{i}": ("adversarial", 5) for i in range(4)}
    b_states = {f"adv-{i}": ("adversarial", 0) for i in range(4)}
    a_states.update({f"ord-{i}": ("ordinary", 5) for i in range(6)})
    b_states.update({f"ord-{i}": ("ordinary", 5) for i in range(6)})
    a = make_record(tmp_path, "a", a_states)
    b = make_record(tmp_path, "b", b_states, "prompts/v2.txt")

    st = compare_stats(a, b, build_flips(a, b))
    assert st["buckets"]["ALL"]["b"] == 4 and st["buckets"]["ALL"]["c"] == 0
    assert st["min_achievable_p"] == pytest.approx(0.125)
    assert "UNDERPOWERED, NOT NULL" in st["verdict"]
    assert "Do not report this as a null result." in st["verdict"]


def test_report_never_prints_nan(tmp_path):
    """find_mde returns nan when no effect reaches 80% power, which is true and
    meaningful. Printing it as 'nan absolute' is neither."""
    from harness.__main__ import build_flips, compare_stats

    a = make_record(tmp_path, "a", {f"c{i}": ("ordinary", 5) for i in range(4)})
    b = make_record(tmp_path, "b", {f"c{i}": ("ordinary", 0) for i in range(4)})
    st = compare_stats(a, b, build_flips(a, b))
    md = report.compare_report(a, b, build_flips(a, b), st)
    # A word-boundary match, because "cannot" contains "nan" and the naive
    # substring check fails on the very sentence this test exists to protect.
    assert not re.search(r"\bnan\b", md, re.IGNORECASE), "NaN leaked into the report"
    assert "smallest two-sided p" in md
    assert "no effect is detectable at all" in md


def test_report_regenerates_a_cmp_record(tmp_path, monkeypatch):
    """`harness report <cmp-dir>` used to call load_record on the cmp directory
    first and die on its missing manifest.json. A cmp record is recognised by
    compare.json. Regeneration is derived from the stored flips and stats, so
    the rewritten report is byte-identical to the one compare wrote."""
    from harness.__main__ import cmd_compare, cmd_report

    a = make_record(tmp_path, "run-a", {"c1": ("ordinary", 5)})
    b = make_record(tmp_path, "run-b", {"c1": ("ordinary", 5)}, "prompts/v2.txt")
    monkeypatch.setattr(records, "RUNS_DIR", str(tmp_path))

    class CmpArgs:
        run_a, run_b = a["path"], b["path"]

    assert cmd_compare(CmpArgs()) == 0
    cmp_dir = next(d for d in tmp_path.iterdir() if d.name.startswith("cmp-"))
    first = (cmp_dir / "report.md").read_text()
    (cmp_dir / "report.md").unlink()

    class RepArgs:
        record = str(cmp_dir)

    assert cmd_report(RepArgs()) == 0
    assert (cmp_dir / "report.md").read_text() == first


def test_underpowered_verdict_does_not_claim_unanimity_on_a_mixed_split():
    """b=4, c=1 is underpowered (5 discordant, smallest p 0.0625) and the
    bootstrap can exclude zero, but the pairs did not all go the same way. The
    old template said they did; the flagship committed comparison carried that
    sentence with a 4/1 split."""
    floor = {"splits": 1000, "p95_mean_delta": 0.1, "n_cases": 15}
    mixed = report.verdict({"b": 4, "c": 1, "p": 0.375}, -0.35, stats_interval(-0.57, -0.12),
                           floor, float("nan"), 0.0625)
    assert mixed.startswith("UNDERPOWERED, NOT NULL")
    assert "went the same way" not in mixed
    assert "split 4 to 1" in mixed
    unanimous = report.verdict({"b": 5, "c": 0, "p": 0.0625}, -0.35, stats_interval(-0.57, -0.12),
                               floor, float("nan"), 0.0625)
    assert "Every one of the 5 discordant pair(s) went the same way" in unanimous


def stats_interval(lo, hi):
    from harness import stats
    return stats.Interval(lo, hi)


def test_empty_reruns_stay_out_of_the_noise_floor(tmp_path):
    """An empty generation is missing data on the deterministic side (all_passed
    is None). bool(None) is False, so without a filter it entered the A/A floor
    as a failure and inflated it; both reviewers reproduced the flip to
    'NOT distinguishable from rerun noise' on an all-pass arm."""
    import json
    a = make_record(tmp_path, "a", {f"c{i}": ("ordinary", 5) for i in range(6)})
    b = make_record(tmp_path, "b", {f"c{i}": ("ordinary", 5) for i in range(6)}, "prompts/v2.txt")
    clean = compare_stats(a, b, build_flips(a, b))["noise_floor"]["p95_mean_delta"]
    # mark two reruns of c0 in A empty, the way the runner writes them
    rows = records.read_jsonl(os.path.join(a["path"], "results.jsonl"))
    for r in rows:
        if r["case_id"] == "c0" and r["rerun"] in (0, 1):
            r["all_passed"] = None
            r["empty"] = True
    with open(os.path.join(a["path"], "results.jsonl"), "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    a["summary"]["c0"]["conjunction"] = {"passes": 3, "n": 3}
    a["summary"]["c0"]["empty"] = 2
    a = records.load_record(a["path"])
    with_empties = compare_stats(a, b, build_flips(a, b))["noise_floor"]["p95_mean_delta"]
    assert clean == 0.0 and with_empties == 0.0


def test_compare_refuses_different_case_id_sets(tmp_path, capsys):
    """Same case files, different --case selection: the file hashes match and
    the old guard let it through, silently intersecting to the shared cases."""
    from harness.__main__ import cmd_compare
    a = make_record(tmp_path, "a", {"c1": ("ordinary", 5), "c2": ("ordinary", 5), "c3": ("ordinary", 5)})
    b = make_record(tmp_path, "b", {"c1": ("ordinary", 5)})

    class Args:
        run_a, run_b = a["path"], b["path"]

    assert cmd_compare(Args()) == 2
    err = capsys.readouterr().err
    assert "different case ids" in err and "c2" in err and "c3" in err
    assert not [d for d in tmp_path.iterdir() if d.name.startswith("cmp-")]


def test_compare_refuses_when_nothing_is_pairable(tmp_path, monkeypatch, capsys):
    """Every shared case nodata on one side used to pass compare_stats, then die
    with KeyError('ALL') in the report after the cmp directory existed."""
    from harness.__main__ import cmd_compare
    a = make_record(tmp_path, "a", {"c1": ("ordinary", 5)})
    b = make_record(tmp_path, "b", {"c1": ("ordinary", 5)})
    b["summary"]["c1"]["conjunction"] = {"passes": 0, "n": 0}
    import json
    with open(os.path.join(b["path"], "summary.json"), "w") as fh:
        json.dump(b["summary"], fh)
    monkeypatch.setattr(records, "RUNS_DIR", str(tmp_path))

    class Args:
        run_a, run_b = a["path"], b["path"]

    assert cmd_compare(Args()) == 2
    assert "nothing to pair" in capsys.readouterr().err
    assert not [d for d in tmp_path.iterdir() if d.name.startswith("cmp-")]


def test_cmp_record_carries_provenance_and_report_recomputes_verdict(tmp_path, monkeypatch):
    """Two comparisons of the same runs can differ only by code. compare.json
    now names the harness commit and the clock, outside the hashed inputs, and
    report.md recomputes the verdict from the stored numbers so a corrected
    template reaches old records on regeneration."""
    import json
    from harness.__main__ import cmd_compare, cmd_report
    a = make_record(tmp_path, "a", {"c1": ("ordinary", 5), "c2": ("ordinary", 0)})
    b = make_record(tmp_path, "b", {"c1": ("ordinary", 5), "c2": ("ordinary", 5)}, "prompts/v2.txt")
    monkeypatch.setattr(records, "RUNS_DIR", str(tmp_path))

    class Args:
        run_a, run_b = a["path"], b["path"]

    assert cmd_compare(Args()) == 0
    cmp_dir = next(d for d in tmp_path.iterdir() if d.name.startswith("cmp-"))
    info = json.load(open(cmp_dir / "compare.json"))
    assert "harness_git_sha" in info and "started" in info
    st = json.load(open(cmp_dir / "stats.json"))
    assert "ci_lo" in st["bootstrap"] and "ci_hi" in st["bootstrap"]
    # poison the stored verdict; regeneration must not echo it
    st["verdict"] = "STALE TEMPLATE TEXT"
    json.dump(st, open(cmp_dir / "stats.json", "w"))

    class RepArgs:
        record = str(cmp_dir)

    assert cmd_report(RepArgs()) == 0
    assert "STALE TEMPLATE TEXT" not in (cmp_dir / "report.md").read_text()


def test_compare_report_warns_when_builds_differ(hidden_regression):
    a, b = hidden_regression
    b["manifest"]["model"]["server_reported"] = "some-other-build"
    flips = build_flips(a, b)
    md = report.compare_report(a, b, flips, compare_stats(a, b, flips))
    assert "different served builds" in md
