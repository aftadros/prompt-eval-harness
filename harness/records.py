"""Run records: hashing, directory layout, append-only enforcement.

A record is self-contained. The prompt is copied in rather than referenced, every
raw output is stored verbatim, and the manifest pins the sha of everything that
went in. The reason is not tidiness. Six weeks from now the only thing standing
between a number in a report and "I think that was the version with the citation
rule" is whether the run wrote down what it ran.

Append-only is enforced rather than documented: `records.py` refuses to write
into an existing record directory. The only file regenerated in place is
`report.md`, which is derived from the record and holds no information of its
own.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
from datetime import date, datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS_DIR = os.path.join(REPO_ROOT, "runs")


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: str) -> str:
    return sha256_bytes(open(path, "rb").read())


def canonical(obj) -> str:
    """Sorted-key, no-whitespace JSON. The hash input, and the only one."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def manifest_hash(manifest: dict) -> str:
    return hashlib.sha256(canonical(manifest).encode("utf-8")).hexdigest()


def git_sha() -> str:
    """The harness commit, read without shelling out to git."""
    head = os.path.join(REPO_ROOT, ".git", "HEAD")
    if not os.path.exists(head):
        return "unknown"
    ref = open(head).read().strip()
    if ref.startswith("ref: "):
        path = os.path.join(REPO_ROOT, ".git", ref[5:])
        if os.path.exists(path):
            return open(path).read().strip()
        packed = os.path.join(REPO_ROOT, ".git", "packed-refs")
        if os.path.exists(packed):
            want = ref[5:]
            for line in open(packed):
                if line.rstrip().endswith(" " + want):
                    return line.split()[0]
        return "unborn"
    return ref


def corpus_hashes(cases) -> dict[str, str]:
    """Every fixture file any case in the set references, hashed.

    Inline context docs are hashed by content under their case-scoped id, so a
    silently edited injection payload changes the manifest exactly as a silently
    edited fixture file would.
    """
    out: dict[str, str] = {}
    for case in cases:
        for doc in case.context:
            if doc.path:
                out[os.path.relpath(doc.path, REPO_ROOT)] = sha256_file(doc.path)
            else:
                out[f"inline:{case.id}:{doc.id}"] = sha256_text(doc.text)
    return dict(sorted(out.items()))


def case_file_hashes(cases_dir: str | None = None) -> dict[str, str]:
    cases_dir = cases_dir or os.path.join(REPO_ROOT, "cases")
    out = {}
    for stem in ("ordinary", "known_hard", "adversarial"):
        p = os.path.join(cases_dir, f"{stem}.yaml")
        if os.path.exists(p):
            out[f"{stem}.yaml"] = sha256_file(p)
    return out


def build_manifest(
    *,
    prompt_path: str,
    cases,
    model_entry: dict,
    model_name: str,
    server_reported: str,
    decoding,
    n_reruns: int,
    judge_info: dict | None = None,
) -> dict:
    prompt_abs = os.path.join(REPO_ROOT, prompt_path)
    return {
        "prompt": {
            "path": prompt_path,
            "sha256": sha256_file(prompt_abs),
        },
        "cases": case_file_hashes(),
        "corpus": corpus_hashes(cases),
        "judge": judge_info,
        "model": {
            "name": model_name,
            "kind": model_entry["kind"],
            "base_url": model_entry.get("base_url"),
            "requested": model_entry["model"],
            "server_reported": server_reported,
        },
        "decoding": decoding.as_dict(),
        "n_reruns": n_reruns,
        "n_cases": len(cases),
        "harness_git_sha": git_sha(),
        "python": platform.python_version(),
        "started": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def new_record_dir(prefix: str, manifest: dict, runs_dir: str | None = None) -> str:
    """Allocate `<prefix>-<YYYY-MM-DD>-<sha12>-<seq>`.

    The hash pins the inputs. The date and sequence exist because temperature is
    nonzero on purpose, so identical inputs legitimately produce different runs
    and collapsing them onto one directory would lose data rather than deduplicate
    it.
    """
    runs_dir = runs_dir or RUNS_DIR
    os.makedirs(runs_dir, exist_ok=True)
    sha12 = manifest_hash(manifest)[:12]
    stamp = date.today().isoformat()
    seq = 1
    while True:
        name = f"{prefix}-{stamp}-{sha12}-{seq}"
        path = os.path.join(runs_dir, name)
        try:
            # mkdir is the atomic claim. Two allocators racing for the same seq
            # both saw it absent; exactly one creates it and the other moves on.
            os.mkdir(path)
            return path
        except FileExistsError:
            seq += 1


def write_json(path: str, obj) -> None:
    _refuse_overwrite(path)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")


def write_text(path: str, text: str) -> None:
    _refuse_overwrite(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def write_report(path: str, text: str) -> None:
    """The one derived file that may be regenerated in place."""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def append_jsonl(path: str, obj) -> None:
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(canonical(obj) + "\n")


def read_jsonl(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def _refuse_overwrite(path: str) -> None:
    if os.path.exists(path):
        raise FileExistsError(
            f"{path} already exists. Records are append-only: a run is evidence, and "
            "rewriting one turns it into an assertion. Make a new record instead."
        )


def load_record(path: str) -> dict:
    """Read a record back: manifest, summary, results, judge rows."""
    if not os.path.isdir(path):
        raise FileNotFoundError(f"no record directory at {path}")
    manifest_path = os.path.join(path, "manifest.json")
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"{path} has no manifest.json, so it is not a record")
    return {
        "path": path,
        "name": os.path.basename(path),
        "manifest": json.load(open(manifest_path, encoding="utf-8")),
        "summary": (
            json.load(open(os.path.join(path, "summary.json"), encoding="utf-8"))
            if os.path.exists(os.path.join(path, "summary.json"))
            else {}
        ),
        "results": read_jsonl(os.path.join(path, "results.jsonl")),
        "judge": read_jsonl(os.path.join(path, "judge.jsonl")),
    }


def resolve(path_or_name: str, runs_dir: str | None = None) -> str:
    """Accept a bare record name or a path."""
    runs_dir = runs_dir or RUNS_DIR
    if os.path.isdir(path_or_name):
        return os.path.normpath(os.path.abspath(path_or_name))
    # A bare name is one path component inside runs/. Anything with a
    # separator or a parent reference is a path, and a path that does not
    # exist is simply not found rather than joined under runs/.
    if os.sep in path_or_name or path_or_name in ("", ".", ".."):
        raise FileNotFoundError(f"no record found at {path_or_name!r}")
    candidate = os.path.normpath(os.path.join(runs_dir, path_or_name))
    if os.path.isdir(candidate):
        return candidate
    raise FileNotFoundError(f"no record found at {path_or_name!r}")
