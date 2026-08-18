"""Substring and format checks."""

from __future__ import annotations

import json

from checks import CheckResult, render_name


def _offset_line(output: str, needle: str) -> str:
    i = output.lower().find(needle.lower())
    start = max(0, i - 30)
    snippet = output[start : i + len(needle) + 30].replace("\n", " ")
    return f"found {needle!r} at offset {i}: ...{snippet}..."


def must_contain(output: str, case, params) -> CheckResult:
    """Passes when every listed substring appears, case-insensitively."""
    needles = list(params or [])
    missing = [n for n in needles if n.lower() not in output.lower()]
    name = render_name("must_contain", needles)
    if missing:
        return CheckResult(name, False, f"missing {missing!r}")
    return CheckResult(name, True, f"all {len(needles)} required span(s) present")


def must_not_contain(output: str, case, params) -> CheckResult:
    """Passes when none of the listed substrings appears.

    This is the trap check. The forbidden span is usually a number or a phrase
    that sits inside the retrieved passage as a counter-example, so a model that
    pattern-matches instead of reading will emit it.
    """
    needles = list(params or [])
    hits = [n for n in needles if n.lower() in output.lower()]
    name = render_name("must_not_contain", needles)
    if hits:
        return CheckResult(name, False, _offset_line(output, hits[0]))
    return CheckResult(name, True, f"none of {len(needles)} forbidden span(s) present")


def valid_json(output: str, case, params=None) -> CheckResult:
    """Passes when the output parses as JSON, after stripping a fenced code block."""
    text = output.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 2:
            lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
    try:
        json.loads(text)
    except (ValueError, TypeError) as exc:
        return CheckResult("valid_json", False, f"parse failed: {exc}")
    return CheckResult("valid_json", True, f"parsed {len(text)} chars as JSON")
