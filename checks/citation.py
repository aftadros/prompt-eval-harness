"""Citation checks.

Citations are a prompt contract, not adapter output. The prompt under test is
required to cite inline as `[doc-id]`; these checks parse the raw text. That
keeps the model adapter text-in/text-out and puts the citation format itself
inside what is being evaluated, which is where it belongs: a prompt change that
quietly breaks the citation format is exactly the kind of regression this
harness exists to catch.
"""

from __future__ import annotations

import re

from checks import CheckResult

#: A citation marker.
#:
#: Doc ids are fixture filename stems, so they start with a letter and always
#: contain at least one hyphen (usually a `--` separating slug from section).
#: The pattern requires both, which is what keeps ordinary bracketed prose out:
#: a footnote marker like `[1]`, an editorial `[sic]`, or `[see note]` are not
#: citations, and an earlier, looser pattern counted `[1]` as one. That mattered
#: more than it looks. `must_not_cite` runs on refusals, so a false positive
#: there fails a correct refusal for containing a bracketed number, and the
#: harness would have reported a prompt regression that was its own bug.
#:
#: The contract is enforced rather than assumed: `harness.cases` rejects a
#: context doc whose id could not be cited under this pattern, so an
#: uncitable-by-construction id fails at load time instead of silently making
#: must_cite unpassable at run time.
CITATION_RE = re.compile(r"\[([a-z][a-z0-9]*(?:-+[a-z0-9]+)+)\]")


def cited_ids(output: str) -> list[str]:
    """Every doc id cited in the output, in order, with duplicates kept."""
    return CITATION_RE.findall(output)


def must_cite(output: str, case, params=None) -> CheckResult:
    """Passes when the output cites at least one doc present in this case's context."""
    available = set(case.doc_ids())
    found = cited_ids(output)
    hits = [c for c in found if c in available]
    if hits:
        return CheckResult("must_cite", True, f"cited [{hits[0]}]")
    if found:
        return CheckResult(
            "must_cite", False, f"cited {found[:3]}, none of which is in this case's context"
        )
    return CheckResult("must_cite", False, "no [doc-id] citation in the output")


def must_not_cite(output: str, case, params=None) -> CheckResult:
    """Passes when the output cites nothing.

    Used on no-answer cases: an honest refusal has nothing to cite, and a refusal
    that cites a source is claiming support it does not have.
    """
    found = cited_ids(output)
    if not found:
        return CheckResult("must_not_cite", True, "no citation markers present")
    return CheckResult("must_not_cite", False, f"cited {found[:3]} while refusing")


def cited_ids_exist(output: str, case, params=None) -> CheckResult:
    """Passes when every cited doc id is one this case actually supplied.

    A fabricated citation is worse than none: it looks like grounding and audits
    clean until somebody follows the link.
    """
    available = set(case.doc_ids())
    found = cited_ids(output)
    bogus = [c for c in found if c not in available]
    if not found:
        return CheckResult("cited_ids_exist", True, "no citations to verify")
    if bogus:
        return CheckResult(
            "cited_ids_exist", False, f"cited {bogus[:3]} which is not in this case's context"
        )
    return CheckResult("cited_ids_exist", True, f"all {len(found)} citation(s) resolve")
