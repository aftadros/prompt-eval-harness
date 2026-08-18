"""Refusal detection.

This is the weakest check in the repo and it is worth saying so where the code
lives rather than in a footnote. Detecting a refusal by pattern-matching English
is the same losing game as detecting sentiment by counting adjectives: every
phrasing you did not think of reads as a non-refusal, and every hedge that
happens to contain "cannot" reads as a refusal.

The mitigation is to stop guessing. The prompt under test is required to open a
refusal with a fixed marker phrase, which is legitimate prompt design in its own
right (a machine-readable refusal is what lets a caller route to a fallback), and
the marker turns this into an exact check. The regex below is a fallback for
outputs that refuse in substance while ignoring the contract, and it is
deliberately narrow: it fires on the first sentence only, because a refusal that
arrives in paragraph three has already asserted something first.

`evidence` always records which of the two paths fired, so a run where the marker
never appears and the fallback carries every pass is visible rather than silent.
That pattern means the prompt is not honoring its own contract, which is a
finding about the prompt, not a detail of the check.
"""

from __future__ import annotations

import re

from checks import CheckResult

#: The prompt contract. Kept here as the single definition; prompts/ must open a
#: refusal with exactly this text, and tests assert the two agree.
REFUSAL_MARKER = "I can't answer that from the sources provided."

#: Fallback, applied to the first sentence only.
_FALLBACK_RE = re.compile(
    r"\b("
    r"i (?:can'?t|cannot|am unable to|don'?t have enough to)\s+(?:answer|say|tell|determine|find)"
    r"|the (?:sources?|documents?|provided (?:sources?|documents?|context))\s+(?:do(?:es)?n'?t|do not|does not)\s+"
    r"(?:contain|cover|say|address|mention)"
    r"|there(?:'s| is) nothing in the (?:sources?|documents?|context)"
    r"|(?:that|this) (?:isn'?t|is not) (?:covered|addressed|answered) (?:in|by) the (?:sources?|documents?)"
    r")",
    re.IGNORECASE,
)


def _first_sentence(text: str) -> str:
    stripped = text.strip()
    parts = re.split(r"(?<=[.!?])\s", stripped, maxsplit=1)
    return parts[0] if parts else stripped


def must_refuse(output: str, case, params=None) -> CheckResult:
    """Passes when the output declines to answer.

    Marker first, narrow fallback second. Which path fired is recorded.
    """
    stripped = output.strip()
    if stripped.startswith(REFUSAL_MARKER):
        return CheckResult("must_refuse", True, "opened with the refusal marker (contract)")

    first = _first_sentence(stripped)
    match = _FALLBACK_RE.search(first)
    if match:
        return CheckResult(
            "must_refuse",
            True,
            f"fallback regex matched {match.group(0)!r} in the first sentence "
            f"(marker absent, so the prompt contract was not honored)",
        )

    preview = first[:90].replace("\n", " ")
    return CheckResult("must_refuse", False, f"answered instead of refusing: {preview!r}")
