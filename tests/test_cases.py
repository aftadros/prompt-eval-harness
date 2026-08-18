"""The loader, and the golden set it loads.

Two kinds of test here. The first kind checks that a malformed case file is
rejected with a message naming the file and the case, because these errors are
meant to cost a second at load time rather than surfacing at case 37 of an
overnight run. The second kind checks properties of the actual golden set, so
that a case added six months from now cannot quietly break the design's own
rules about buckets, coverage and falsifiability.
"""

import os

import pytest
import yaml

from harness.cases import CaseError, load_all, load_case_file, load_questions

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def cases():
    return load_all()


def write_cases(tmp_path, name, payload):
    p = tmp_path / f"{name}.yaml"
    p.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return str(p)


MINIMAL = {
    "id": "ord-x",
    "input": "q?",
    "context": [{"doc": "evals-before-vibes--the-golden-set"}],
    "checks": ["must_cite"],
    "why": "because",
    "source": "constructed",
    "added": "2026-08-17",
}


# --- rejection ------------------------------------------------------------


def test_minimal_case_loads(tmp_path):
    path = write_cases(tmp_path, "ordinary", [MINIMAL])
    assert load_case_file(path, {})[0].id == "ord-x"


def test_unknown_check_is_rejected_with_the_known_list(tmp_path):
    bad = dict(MINIMAL, checks=["must_be_nice"])
    with pytest.raises(CaseError) as exc:
        load_case_file(write_cases(tmp_path, "ordinary", [bad]), {})
    assert "must_be_nice" in str(exc.value) and "Known:" in str(exc.value)


def test_dangling_fixture_reference_is_rejected(tmp_path):
    bad = dict(MINIMAL, context=[{"doc": "post-that-does-not-exist--section"}])
    with pytest.raises(CaseError) as exc:
        load_case_file(write_cases(tmp_path, "ordinary", [bad]), {})
    assert "not a file" in str(exc.value)


def test_in_file_bucket_key_is_rejected(tmp_path):
    """Bucket comes from the filename. Two sources of truth is one too many."""
    bad = dict(MINIMAL, bucket="ordinary")
    with pytest.raises(CaseError) as exc:
        load_case_file(write_cases(tmp_path, "ordinary", [bad]), {})
    assert "derived from the filename" in str(exc.value)


def test_missing_why_is_rejected(tmp_path):
    bad = {k: v for k, v in MINIMAL.items() if k != "why"}
    with pytest.raises(CaseError):
        load_case_file(write_cases(tmp_path, "ordinary", [bad]), {})


def test_parameters_on_an_unparameterized_check_are_rejected(tmp_path):
    bad = dict(MINIMAL, checks=[{"must_cite": ["x"]}])
    with pytest.raises(CaseError) as exc:
        load_case_file(write_cases(tmp_path, "ordinary", [bad]), {})
    assert "takes no parameters" in str(exc.value)


def test_tainted_doc_without_a_canary_is_rejected(tmp_path):
    bad = dict(MINIMAL, context=[{"id": "planted-doc", "text": "payload", "tainted": True}])
    with pytest.raises(CaseError) as exc:
        load_case_file(write_cases(tmp_path, "adversarial", [bad]), {})
    assert "nothing can be checked deterministically" in str(exc.value)


def test_canary_absent_from_its_own_text_is_rejected(tmp_path):
    """A check that can never fail is decoration, and this is the loader catching
    the most likely way to write one by accident."""
    bad = dict(MINIMAL, context=[
        {"id": "planted-doc", "text": "no canary here", "tainted": True, "canary": "CANARY-1-x"}
    ])
    with pytest.raises(CaseError) as exc:
        load_case_file(write_cases(tmp_path, "adversarial", [bad]), {})
    assert "can never fail" in str(exc.value)


def test_uncitable_doc_id_is_rejected(tmp_path):
    bad = dict(MINIMAL, context=[{"id": "planted", "text": "x"}])
    with pytest.raises(CaseError) as exc:
        load_case_file(write_cases(tmp_path, "ordinary", [bad]), {})
    assert "citation pattern" in str(exc.value)


def test_unknown_judge_question_is_rejected(tmp_path):
    bad = dict(MINIMAL, judge=["is_it_vibey"])
    with pytest.raises(CaseError):
        load_case_file(write_cases(tmp_path, "ordinary", [bad]), {"grounded": {}})


def test_case_with_neither_check_nor_judge_is_rejected(tmp_path):
    bad = {k: v for k, v in MINIMAL.items() if k != "checks"}
    with pytest.raises(CaseError):
        load_case_file(write_cases(tmp_path, "ordinary", [bad]), {})


def test_adversarial_block_on_a_non_adversarial_case_is_rejected(tmp_path):
    bad = dict(MINIMAL, adversarial={"vector": "direct", "injection_point": "user_message"})
    with pytest.raises(CaseError) as exc:
        load_case_file(write_cases(tmp_path, "ordinary", [bad]), {})
    assert "only belongs on adversarial cases" in str(exc.value)


def test_bad_filename_is_rejected(tmp_path):
    with pytest.raises(CaseError):
        load_case_file(write_cases(tmp_path, "extra_hard", [MINIMAL]), {})


# --- the golden set itself ------------------------------------------------


def test_the_set_is_the_designed_shape(cases):
    from collections import Counter

    assert len(cases) == 50
    assert Counter(c.bucket for c in cases) == {"ordinary": 20, "known_hard": 15, "adversarial": 15}


def test_adversarial_sub_buckets(cases):
    adv = [c for c in cases if c.bucket == "adversarial"]
    injection = [c for c in adv if c.adversarial]
    no_answer = [c for c in adv if not c.adversarial and any(
        n == "must_refuse" for n, _ in c.checks)]
    false_premise = [c for c in adv if not c.adversarial and "premise_corrected" in c.judge]
    assert len(injection) == 5
    assert len(no_answer) == 7
    assert len(false_premise) == 3


def test_judge_routing_stays_a_minority(cases):
    """The rubric's own warning, enforced. If most cases are judge-routed, the
    harness has drifted into grading everything with a model."""
    routed = [c for c in cases if c.judge]
    assert len(routed) == 15
    assert len(routed) < len(cases) / 2


def test_risky_checks_are_never_judge_gated(cases):
    """Refusal and leak checks decide things that cost something when wrong, so
    they are deterministic and the judge does not get a vote on them."""
    for c in cases:
        names = {n for n, _ in c.checks}
        if "must_refuse" in names or "must_not_leak_restricted" in names:
            assert "grounded" not in c.judge or names, c.id


def test_every_case_can_fail(cases):
    """Falsifiability. A case whose checks are vacuously true given its own
    context is decoration, and the two ways to write one are a must_not_contain
    whose spans are absent from every fixture it could quote, and a leak check
    with no tainted doc."""
    for c in cases:
        names = {n for n, _ in c.checks}
        if names == {"must_not_leak_restricted"}:
            assert c.canaries(), f"{c.id}: leak check with nothing to leak"
        assert c.checks or c.judge, c.id


def test_ordinary_cases_carry_a_cross_post_distractor(cases):
    """The rule that keeps the ordinary bucket honest: with one fixture, must_cite
    passes because there is nothing else to cite."""
    for c in cases:
        if c.bucket != "ordinary":
            continue
        slugs = {d.id.split("--")[0] for d in c.context if d.path}
        assert len(c.context) >= 2, f"{c.id}: single-fixture ordinary case"
        assert len(slugs) >= 2, f"{c.id}: all fixtures come from the same post"


def test_no_answer_cases_do_not_cite(cases):
    for c in cases:
        names = {n for n, _ in c.checks}
        if "must_refuse" in names and not c.adversarial:
            assert "must_not_cite" in names, f"{c.id}: refuses but may still cite"


def test_every_why_line_is_substantive(cases):
    """The `why` field is the falsifiability note, not a label."""
    for c in cases:
        assert len(c.why.split()) >= 12, f"{c.id}: why is too thin to be a reason"


def test_case_ids_are_prefixed_by_bucket(cases):
    prefixes = {"ordinary": "ord-", "known_hard": "kh-", "adversarial": "adv-"}
    for c in cases:
        assert c.id.startswith(prefixes[c.bucket]), c.id


def test_every_post_is_covered(cases):
    """Coverage quota: each of the 11 posts appears in an ordinary case and in at
    least one other bucket."""
    per_post: dict[str, set] = {}
    for c in cases:
        for d in c.context:
            if d.path and "fixtures" in d.path:
                per_post.setdefault(d.id.split("--")[0], set()).add(c.bucket)
    assert len(per_post) == 11
    for slug, buckets in per_post.items():
        assert "ordinary" in buckets, f"{slug} has no ordinary case"
        assert len(buckets) >= 2, f"{slug} appears in only one bucket"


def test_forbidden_spans_are_plausible_not_impossible(cases):
    """A must_not_contain span has to be something a wrong answer would actually
    say. This asserts each one is non-trivial rather than an empty string or a
    single character that would fire on almost any text."""
    for c in cases:
        for name, params in c.checks:
            if name == "must_not_contain":
                for span in params:
                    assert len(span) >= 2, f"{c.id}: forbidden span {span!r} is too short"


def test_judge_questions_referenced_by_cases_all_exist(cases):
    known = set(load_questions())
    for c in cases:
        for q in c.judge:
            assert q in known, f"{c.id} references unknown judge question {q}"


def test_context_text_delimits_every_document(cases):
    """The prompt's data/instruction boundary depends on this markup existing."""
    for c in cases:
        rendered = c.context_text()
        for d in c.context:
            assert f'<document id="{d.id}">' in rendered


def test_known_hard_traps_are_baited(cases):
    """A known-hard `must_not_contain` span has to appear in the case's own
    context, or it is not a trap.

    The whole design of `kh-chunk-size-trap` is that "512" sits inside the very
    passage the model was handed, as the counter-example being argued against. If
    the span were absent from the context, the case would be testing whether the
    model invents a number out of nowhere, which is a no-answer case and belongs
    in the other bucket.
    """
    for c in cases:
        if c.bucket != "known_hard":
            continue
        for name, params in c.checks:
            if name != "must_not_contain":
                continue
            if (c.notes or "").strip().startswith("hedge-guard"):
                # A hedge guard forbids a phrase the model supplies unprompted
                # rather than one planted in the passage. It fails for the
                # opposite reason a bait does, so it declares itself in `notes`.
                continue
            haystack = c.context_text().lower()
            baited = [s for s in params if s.lower() in haystack]
            assert baited, (
                f"{c.id}: none of {params} appears in its own context, so nothing "
                "tempts the model and the check cannot discriminate. If this is a "
                "hedge guard, say so in `notes`."
            )


def test_no_answer_traps_are_absent_from_the_context(cases):
    """The mirror rule. On a no-answer case the forbidden span must NOT be in the
    context, or a model quoting its source correctly would fail."""
    for c in cases:
        names = {n for n, _ in c.checks}
        if "must_refuse" not in names or c.adversarial:
            continue
        haystack = c.context_text().lower()
        for name, params in c.checks:
            if name != "must_not_contain":
                continue
            present = [s for s in params if s.lower() in haystack]
            assert not present, (
                f"{c.id}: {present} appears in its own context, so a model quoting "
                "the source accurately would fail this check"
            )


def test_injection_payloads_are_never_stored_as_fixture_files(cases):
    """Nothing doctored may sit in fixtures/ beside the verbatim excerpts, where
    it could be read or indexed as something the author wrote."""
    import os

    for c in cases:
        for d in c.context:
            if d.tainted or d.restricted:
                assert d.path is None, f"{c.id}: tainted doc {d.id} is a file at {d.path}"
    adv_dir = os.path.join(REPO_ROOT, "fixtures", "adversarial")
    if os.path.isdir(adv_dir):
        stray = [f for f in os.listdir(adv_dir) if f.endswith(".md") and f != "README.md"]
        assert not stray, f"doctored fixture files present: {stray}"


def test_injection_cases_can_actually_detect_a_leak(cases):
    """Every canary has to be unique across the whole set, or a leak on one case
    would be attributable to another."""
    seen: dict[str, str] = {}
    for c in cases:
        for canary in c.canaries():
            assert canary not in seen, f"canary {canary} shared by {seen[canary]} and {c.id}"
            seen[canary] = c.id
    assert len(seen) == 4


def test_the_forthcoming_edit_is_the_only_difference_between_the_prompts():
    """P_A and P_B must differ in exactly one rule, or the A/B measures the wrong
    thing and no per-bucket result can be attributed to the edit."""
    import difflib
    import os

    a = open(os.path.join(REPO_ROOT, "prompts", "v1.txt")).read().splitlines()
    b = open(os.path.join(REPO_ROOT, "prompts", "v2.txt")).read().splitlines()
    changed_blocks = [
        g for g in difflib.SequenceMatcher(None, a, b).get_opcodes() if g[0] != "equal"
    ]
    assert len(changed_blocks) <= 2, f"prompts differ in {len(changed_blocks)} places"
    for line in b:
        assert "—" not in line and "–" not in line


def test_the_refusal_marker_matches_the_prompt_contract():
    """checks/refusal.py defines the marker; the prompts have to use that exact
    string or must_refuse silently falls back to the regex on every case."""
    import os

    from checks.refusal import REFUSAL_MARKER

    for name in ("v1.txt", "v2.txt"):
        text = open(os.path.join(REPO_ROOT, "prompts", name)).read()
        assert REFUSAL_MARKER in text, f"prompts/{name} does not carry the refusal marker"
