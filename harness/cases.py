"""Load and validate the golden set.

Everything here fails loudly and early. A case file with an unknown check name,
a dangling fixture reference, or a duplicate id is a config error that should
cost a second at load time, not surface as a stack trace at case 37 of an
overnight run. Validation therefore runs over the whole set before the runner is
allowed to make its first model call.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

import yaml

import checks as checks_pkg

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE_DIRS = ("fixtures", "fixtures/adversarial", "corpus")

BUCKETS = {"ordinary": "ordinary", "known_hard": "known_hard", "adversarial": "adversarial"}
SOURCES = {"reported", "mined", "handbook", "injection-pack", "constructed"}

ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class CaseError(ValueError):
    """A case file is malformed. The message names the file and the case id."""


@dataclass(frozen=True)
class ContextDoc:
    """One entry of what retrieval returned, frozen at authoring time."""

    id: str
    text: str
    tainted: bool = False
    restricted: bool = False
    canary: str | None = None
    #: None for inline docs; the file the text was read from otherwise.
    path: str | None = None


@dataclass(frozen=True)
class Case:
    id: str
    bucket: str
    input: str
    context: tuple[ContextDoc, ...]
    checks: tuple[tuple[str, Any], ...]
    judge: tuple[str, ...]
    why: str
    source: str
    added: str
    adversarial: dict[str, str] | None = None
    notes: str | None = None
    origin_file: str = ""

    def doc_ids(self) -> list[str]:
        return [d.id for d in self.context]

    def canaries(self) -> list[str]:
        return [d.canary for d in self.context if d.canary and (d.tainted or d.restricted)]

    def context_text(self) -> str:
        """The context as the prompt sees it: one delimited block per doc."""
        parts = []
        for d in self.context:
            parts.append(f"<document id=\"{d.id}\">\n{d.text.strip()}\n</document>")
        return "\n\n".join(parts)


def _fixture_path(doc_id: str) -> str | None:
    for d in FIXTURE_DIRS:
        p = os.path.join(REPO_ROOT, d, doc_id + ".md")
        if os.path.exists(p):
            return p
    return None


def _read_fixture(path: str) -> str:
    raw = open(path, encoding="utf-8").read()
    if raw.startswith("---\n"):
        end = raw.find("\n---\n", 4)
        if end != -1:
            raw = raw[end + 5 :]
    return raw.strip()


def _check_citable(doc_id: str, case_id: str, where: str) -> None:
    """A doc id that cannot be cited makes must_cite unpassable for that case."""
    from checks.citation import CITATION_RE

    if not CITATION_RE.fullmatch(f"[{doc_id}]"):
        raise CaseError(
            f"{where}: {case_id}: context doc id {doc_id!r} does not match the citation "
            "pattern (lowercase, starts with a letter, contains a hyphen), so the model "
            "could never produce a citation this harness would recognize"
        )


def _parse_context(entries: Any, case_id: str, where: str) -> tuple[ContextDoc, ...]:
    if entries is None:
        entries = []
    if not isinstance(entries, list):
        raise CaseError(f"{where}: {case_id}: `context` must be a list")
    out: list[ContextDoc] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise CaseError(f"{where}: {case_id}: context entries must be mappings")
        if "doc" in entry:
            if set(entry) != {"doc"}:
                extra = sorted(set(entry) - {"doc"})
                raise CaseError(
                    f"{where}: {case_id}: a `doc:` reference takes no other keys (got {extra})"
                )
            doc_id = entry["doc"]
            path = _fixture_path(doc_id)
            if path is None:
                raise CaseError(
                    f"{where}: {case_id}: context references {doc_id!r}, "
                    f"which is not a file in {'/, '.join(FIXTURE_DIRS)}/"
                )
            _check_citable(doc_id, case_id, where)
            text = _read_fixture(path)
            tainted = "/adversarial/" in path.replace(os.sep, "/")
            out.append(ContextDoc(id=doc_id, text=text, tainted=tainted, path=path))
        elif "id" in entry and "text" in entry:
            unknown = set(entry) - {"id", "text", "tainted", "restricted", "canary"}
            if unknown:
                raise CaseError(f"{where}: {case_id}: unknown context keys {sorted(unknown)}")
            _check_citable(entry["id"], case_id, where)
            doc = ContextDoc(
                id=entry["id"],
                text=entry["text"],
                tainted=bool(entry.get("tainted", False)),
                restricted=bool(entry.get("restricted", False)),
                canary=entry.get("canary"),
            )
            if (doc.tainted or doc.restricted) and not doc.canary:
                raise CaseError(
                    f"{where}: {case_id}: inline doc {doc.id!r} is tainted or restricted "
                    "but carries no canary, so nothing can be checked deterministically"
                )
            if doc.canary and doc.canary not in doc.text:
                raise CaseError(
                    f"{where}: {case_id}: doc {doc.id!r} declares canary {doc.canary!r} "
                    "but the text does not contain it, so the check can never fail"
                )
            out.append(doc)
        else:
            raise CaseError(
                f"{where}: {case_id}: context entry needs either `doc:` or `id:` + `text:`"
            )
    return tuple(out)


def _parse_checks(raw: Any, case_id: str, where: str) -> tuple[tuple[str, Any], ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise CaseError(f"{where}: {case_id}: `checks` must be a list")
    out = []
    for item in raw:
        if isinstance(item, str):
            name, params = item, None
        elif isinstance(item, dict) and len(item) == 1:
            name, params = next(iter(item.items()))
        else:
            raise CaseError(
                f"{where}: {case_id}: a check is either a name or a single-key mapping"
            )
        if name not in checks_pkg.REGISTRY:
            known = ", ".join(sorted(checks_pkg.REGISTRY))
            raise CaseError(f"{where}: {case_id}: unknown check {name!r}. Known: {known}")
        if params is not None and name not in checks_pkg.PARAMETERIZED:
            raise CaseError(f"{where}: {case_id}: check {name!r} takes no parameters")
        if name in checks_pkg.PARAMETERIZED:
            if not isinstance(params, list) or not params:
                raise CaseError(f"{where}: {case_id}: {name!r} needs a non-empty list of strings")
            params = [str(p) for p in params]
        out.append((name, params))
    return tuple(out)


def load_questions(path: str | None = None) -> dict[str, dict]:
    """Judge question ids, so cases can be validated against them."""
    path = path or os.path.join(REPO_ROOT, "judge", "questions.yaml")
    if not os.path.exists(path):
        return {}
    data = yaml.safe_load(open(path, encoding="utf-8")) or []
    return {q["id"]: q for q in data}


def load_case_file(path: str, questions: dict[str, dict]) -> list[Case]:
    where = os.path.basename(path)
    stem = os.path.splitext(where)[0]
    if stem not in BUCKETS:
        raise CaseError(f"{where}: filename must be one of {sorted(BUCKETS)}.yaml")
    bucket = BUCKETS[stem]

    data = yaml.safe_load(open(path, encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise CaseError(f"{where}: expected a non-empty list of cases")

    cases = []
    for raw in data:
        if not isinstance(raw, dict):
            raise CaseError(f"{where}: every case must be a mapping")
        cid = raw.get("id")
        if not cid or not isinstance(cid, str):
            raise CaseError(f"{where}: a case is missing `id`")
        if not ID_RE.match(cid):
            raise CaseError(f"{where}: {cid!r} is not kebab-case")
        if "bucket" in raw:
            raise CaseError(
                f"{where}: {cid}: `bucket` is derived from the filename; "
                "an in-file key would be a second source of truth"
            )
        unknown = set(raw) - {
            "id", "input", "context", "checks", "judge", "why",
            "source", "added", "adversarial", "notes",
        }
        if unknown:
            raise CaseError(f"{where}: {cid}: unknown keys {sorted(unknown)}")

        for req in ("input", "why", "source", "added"):
            if not raw.get(req):
                raise CaseError(f"{where}: {cid}: `{req}` is required")
        if raw["source"] not in SOURCES:
            raise CaseError(f"{where}: {cid}: source must be one of {sorted(SOURCES)}")

        context = _parse_context(raw.get("context", []), cid, where)
        parsed_checks = _parse_checks(raw.get("checks"), cid, where)

        judge = tuple(raw.get("judge") or ())
        for q in judge:
            if questions and q not in questions:
                raise CaseError(f"{where}: {cid}: unknown judge question {q!r}")
        if not parsed_checks and not judge:
            raise CaseError(f"{where}: {cid}: needs at least one check or judge question")

        adversarial = raw.get("adversarial")
        if bucket == "adversarial" and adversarial is not None:
            if set(adversarial) != {"vector", "injection_point"}:
                raise CaseError(f"{where}: {cid}: `adversarial` needs vector + injection_point")
            if adversarial["vector"] not in ("direct", "indirect"):
                raise CaseError(f"{where}: {cid}: vector must be direct or indirect")
            if adversarial["injection_point"] not in ("user_message", "retrieved_doc"):
                raise CaseError(f"{where}: {cid}: injection_point must be user_message or retrieved_doc")
        elif adversarial is not None:
            raise CaseError(f"{where}: {cid}: `adversarial` only belongs on adversarial cases")

        added = str(raw["added"])
        cases.append(
            Case(
                id=cid,
                bucket=bucket,
                input=raw["input"],
                context=context,
                checks=parsed_checks,
                judge=judge,
                why=raw["why"].strip(),
                source=raw["source"],
                added=added,
                adversarial=adversarial,
                notes=raw.get("notes"),
                origin_file=where,
            )
        )
    return cases


def load_all(cases_dir: str | None = None) -> list[Case]:
    """Load every bucket, rejecting duplicate ids across files."""
    cases_dir = cases_dir or os.path.join(REPO_ROOT, "cases")
    questions = load_questions()
    out: list[Case] = []
    for stem in ("ordinary", "known_hard", "adversarial"):
        path = os.path.join(cases_dir, f"{stem}.yaml")
        if os.path.exists(path):
            out.extend(load_case_file(path, questions))
    seen: dict[str, str] = {}
    for c in out:
        if c.id in seen:
            raise CaseError(f"duplicate case id {c.id!r} in {seen[c.id]} and {c.origin_file}")
        seen[c.id] = c.origin_file
    return out
