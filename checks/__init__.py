"""Deterministic property checks.

A check answers one yes/no question about an output, using only the output text
and the case that produced it. Checks are pure: no I/O, no randomness, no
network, no access to the model or the run record. That is what makes them cheap
to run, stable between runs, and safe to trust on the cases that carry risk.

Adding a check is one pure function plus one line in REGISTRY. Discovery is a
dict literal rather than a scan, so `grep REGISTRY` is the complete list.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:  # avoids a cycle: harness.cases validates against REGISTRY
    from harness.cases import Case


@dataclass(frozen=True)
class CheckResult:
    """One check's verdict on one output.

    `evidence` is mandatory even when the check passes. Every row in a report has
    to point at text, because the first question anyone asks about a red cell is
    "where?" and the second is "are you sure?".
    """

    name: str
    passed: bool
    evidence: str


CheckFn = Callable[[str, "Case", Any], CheckResult]


def render_name(name: str, params: Any) -> str:
    """Human-readable check name including its parameters."""
    if params is None:
        return name
    if isinstance(params, (list, tuple)):
        return f"{name}:{','.join(str(p) for p in params)}"
    return f"{name}:{params}"


from checks import citation, containment, leak, refusal  # noqa: E402

REGISTRY: dict[str, CheckFn] = {
    "must_cite": citation.must_cite,
    "must_not_cite": citation.must_not_cite,
    "cited_ids_exist": citation.cited_ids_exist,
    "must_contain": containment.must_contain,
    "must_not_contain": containment.must_not_contain,
    "must_refuse": refusal.must_refuse,
    "must_not_leak_restricted": leak.must_not_leak_restricted,
    "valid_json": containment.valid_json,
}

#: Checks that take a parameter. Everything else is rejected at load time if one
#: is supplied, so a typo in a case file fails before any model call.
PARAMETERIZED = {"must_contain", "must_not_contain"}

__all__ = ["CheckResult", "CheckFn", "REGISTRY", "PARAMETERIZED", "render_name"]
