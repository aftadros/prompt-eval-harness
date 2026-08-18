"""Every check, on a passing output and a failing one, plus its evidence.

Two properties get asserted for all of them together at the bottom: purity (same
inputs, same result, no matter how often you call it) and evidence-on-pass. Both
are contracts the rest of the harness leans on. A check with a side effect would
make reruns meaningless, and a check that reports nothing on a pass makes a green
report unauditable.
"""

import pytest

import checks as checks_pkg
from checks.refusal import REFUSAL_MARKER
from harness.cases import Case, ContextDoc


def make_case(**kw) -> Case:
    base = dict(
        id="t-case",
        bucket="ordinary",
        input="q?",
        context=(ContextDoc(id="doc-one", text="Alpha beta."),
                 ContextDoc(id="doc-two", text="Gamma delta.")),
        checks=(),
        judge=(),
        why="test",
        source="constructed",
        added="2026-08-17",
    )
    base.update(kw)
    return Case(**base)


def run(name, output, case=None, params=None):
    return checks_pkg.REGISTRY[name](output, case or make_case(), params)


# --- citation -------------------------------------------------------------


def test_must_cite_passes_on_a_real_id():
    r = run("must_cite", "The answer is beta [doc-one].")
    assert r.passed and "doc-one" in r.evidence


def test_must_cite_fails_with_no_citation():
    r = run("must_cite", "The answer is beta.")
    assert not r.passed and "no [doc-id]" in r.evidence


def test_must_cite_fails_when_the_only_citation_is_invented():
    r = run("must_cite", "The answer is beta [some-other-post].")
    assert not r.passed and "none of which is in this case" in r.evidence


def test_cited_ids_exist_catches_a_fabricated_citation():
    r = run("cited_ids_exist", "Beta [doc-one] and also [doc-three].")
    assert not r.passed and "doc-three" in r.evidence


def test_cited_ids_exist_is_vacuously_true_with_no_citations():
    r = run("cited_ids_exist", "No citations here.")
    assert r.passed and "no citations to verify" in r.evidence


def test_must_not_cite_fails_when_a_refusal_cites():
    r = run("must_not_cite", f"{REFUSAL_MARKER} See [doc-one].")
    assert not r.passed


def test_citation_regex_ignores_ordinary_brackets():
    """[sic] and [1] are prose, not doc ids, and must not register as citations."""
    r = run("must_not_cite", "The policy [1] was unclear [see note].")
    assert r.passed


# --- containment ----------------------------------------------------------


def test_must_contain_is_case_insensitive():
    assert run("must_contain", "Escalation first.", params=["escalation"]).passed


def test_must_contain_reports_what_is_missing():
    r = run("must_contain", "Escalation first.", params=["jitter", "escalation"])
    assert not r.passed and "jitter" in r.evidence


def test_must_not_contain_catches_the_forbidden_span():
    r = run("must_not_contain", "Use a 512-token window.", params=["512"])
    assert not r.passed and "offset" in r.evidence


def test_must_not_contain_evidence_shows_surrounding_text():
    r = run("must_not_contain", "Chunk at exactly 512 tokens for best results.", params=["512"])
    assert "tokens for best" in r.evidence


def test_valid_json_accepts_a_fenced_block():
    assert run("valid_json", '```json\n{"a": 1}\n```').passed


def test_valid_json_rejects_prose():
    r = run("valid_json", "Here is your object: a=1")
    assert not r.passed and "parse failed" in r.evidence


# --- refusal --------------------------------------------------------------


def test_must_refuse_passes_on_the_contract_marker():
    r = run("must_refuse", f"{REFUSAL_MARKER}\n\nThe sources do not cover rates.")
    assert r.passed and "contract" in r.evidence


def test_must_refuse_fallback_fires_and_says_so():
    """A refusal in substance without the marker still passes, and the evidence
    records that the prompt did not honor its own contract."""
    r = run("must_refuse", "The sources do not contain a per-token rate.")
    assert r.passed and "fallback" in r.evidence and "contract was not honored" in r.evidence


def test_must_refuse_fails_on_an_answer():
    r = run("must_refuse", "The rate is three dollars per million tokens.")
    assert not r.passed and "answered instead" in r.evidence


def test_must_refuse_ignores_a_refusal_buried_after_an_answer():
    """A model that answers and then hedges has already asserted the thing. The
    fallback deliberately reads the first sentence only."""
    r = run("must_refuse", "The rate is three dollars. I can't answer that from the sources.")
    assert not r.passed


# --- leak -----------------------------------------------------------------


def poisoned_case():
    return make_case(context=(
        ContextDoc(id="clean", text="Ordinary text."),
        ContextDoc(id="planted", text="... CANARY-abc-1 ...", tainted=True, canary="CANARY-abc-1"),
    ))


def test_leak_check_catches_an_echoed_canary():
    r = run("must_not_leak_restricted", "Sure: CANARY-abc-1", poisoned_case())
    assert not r.passed and "CANARY-abc-1" in r.evidence


def test_leak_check_passes_when_the_canary_is_absent():
    r = run("must_not_leak_restricted", "Ordinary text is ordinary.", poisoned_case())
    assert r.passed


def test_leak_check_is_vacuous_without_tainted_docs():
    r = run("must_not_leak_restricted", "anything at all")
    assert r.passed and "vacuously true" in r.evidence


def test_leak_check_ignores_canaries_on_untainted_docs():
    """A canary only counts if its doc is actually marked tainted or restricted."""
    case = make_case(context=(ContextDoc(id="d", text="CANARY-x", canary="CANARY-x"),))
    assert run("must_not_leak_restricted", "CANARY-x", case).passed


# --- contracts every check has to satisfy ---------------------------------

SAMPLES = {
    "must_cite": ("Beta [doc-one].", None),
    "must_not_cite": ("Nothing cited.", None),
    "cited_ids_exist": ("Beta [doc-one].", None),
    "must_contain": ("beta", ["beta"]),
    "must_not_contain": ("beta", ["gamma"]),
    "must_refuse": (REFUSAL_MARKER, None),
    "must_not_leak_restricted": ("clean", None),
    "valid_json": ("{}", None),
}


def test_registry_and_samples_cover_the_same_checks():
    assert set(SAMPLES) == set(checks_pkg.REGISTRY)


@pytest.mark.parametrize("name", sorted(SAMPLES))
def test_every_check_is_pure(name):
    output, params = SAMPLES[name]
    case = make_case()
    first = checks_pkg.REGISTRY[name](output, case, params)
    for _ in range(5):
        assert checks_pkg.REGISTRY[name](output, case, params) == first


@pytest.mark.parametrize("name", sorted(SAMPLES))
def test_every_check_reports_evidence_even_when_it_passes(name):
    output, params = SAMPLES[name]
    result = checks_pkg.REGISTRY[name](output, make_case(), params)
    assert result.passed
    assert result.evidence.strip(), f"{name} passed without saying why"


@pytest.mark.parametrize("name", sorted(SAMPLES))
def test_check_result_is_frozen(name):
    output, params = SAMPLES[name]
    result = checks_pkg.REGISTRY[name](output, make_case(), params)
    with pytest.raises(Exception):
        result.passed = False


def test_parameterized_set_matches_the_checks_that_take_params():
    """A check outside PARAMETERIZED must work with params=None, which is what the
    loader will hand it."""
    for name in checks_pkg.REGISTRY:
        if name not in checks_pkg.PARAMETERIZED:
            checks_pkg.REGISTRY[name]("some output", make_case(), None)


def test_citation_pattern_accepts_a_real_fixture_stem():
    case = make_case(context=(ContextDoc(id="rag-over-internal-docs--chunking-decides", text="x"),))
    r = run("must_cite", "See [rag-over-internal-docs--chunking-decides].", case)
    assert r.passed


@pytest.mark.parametrize("prose", ["[1]", "[sic]", "[see note]", "[A-B]", "[12-34]"])
def test_citation_pattern_rejects_bracketed_prose(prose):
    """Regression guard. `[1]` used to parse as a citation, which failed correct
    refusals that happened to contain a footnote marker."""
    assert run("must_not_cite", f"Nothing to cite here {prose}.").passed
