"""Record hashing and the append-only rule.

The append-only rule is the one thing here that is a claim about integrity rather
than about convenience, so it gets a test rather than a paragraph.
"""

import os

import pytest

from harness import records


def test_canonical_json_is_key_order_independent():
    """Manifest hashing depends on this: two dicts with the same content have to
    hash the same however they were built."""
    a = {"b": 1, "a": {"d": 2, "c": 3}}
    b = {"a": {"c": 3, "d": 2}, "b": 1}
    assert records.canonical(a) == records.canonical(b)
    assert records.manifest_hash(a) == records.manifest_hash(b)


def test_manifest_hash_is_stable_across_calls():
    m = {"prompt": {"sha256": "sha256:abc"}, "n_reruns": 5}
    assert records.manifest_hash(m) == records.manifest_hash(m)


def test_manifest_hash_changes_when_any_input_changes():
    base = {"prompt": {"path": "prompts/v1.txt"}, "n_reruns": 5}
    changed = {"prompt": {"path": "prompts/v2.txt"}, "n_reruns": 5}
    assert records.manifest_hash(base) != records.manifest_hash(changed)


def test_sha256_helpers_agree_with_each_other(tmp_path):
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    assert records.sha256_file(str(p)) == records.sha256_text("hello")


def test_write_json_refuses_to_overwrite(tmp_path):
    p = str(tmp_path / "manifest.json")
    records.write_json(p, {"a": 1})
    with pytest.raises(FileExistsError) as exc:
        records.write_json(p, {"a": 2})
    assert "append-only" in str(exc.value)


def test_write_text_refuses_to_overwrite(tmp_path):
    p = str(tmp_path / "out.txt")
    records.write_text(p, "first")
    with pytest.raises(FileExistsError):
        records.write_text(p, "second")


def test_report_is_the_one_file_that_may_be_regenerated(tmp_path):
    p = str(tmp_path / "report.md")
    records.write_report(p, "v1")
    records.write_report(p, "v2")
    assert open(p).read() == "v2"


def test_new_record_dir_never_reuses_a_directory(tmp_path):
    m = {"same": "inputs"}
    first = records.new_record_dir("run", m, runs_dir=str(tmp_path))
    second = records.new_record_dir("run", m, runs_dir=str(tmp_path))
    assert first != second
    # Identical inputs share the hash and differ only by sequence: temperature is
    # nonzero on purpose, so two runs of the same thing are two real runs.
    assert os.path.basename(first).rsplit("-", 1)[0] == os.path.basename(second).rsplit("-", 1)[0]


def test_append_jsonl_round_trips(tmp_path):
    p = str(tmp_path / "rows.jsonl")
    records.append_jsonl(p, {"a": 1})
    records.append_jsonl(p, {"a": 2})
    assert [r["a"] for r in records.read_jsonl(p)] == [1, 2]


def test_read_jsonl_of_a_missing_file_is_empty():
    assert records.read_jsonl("/nonexistent/path.jsonl") == []


def test_load_record_rejects_a_directory_with_no_manifest(tmp_path):
    with pytest.raises(FileNotFoundError) as exc:
        records.load_record(str(tmp_path))
    assert "not a record" in str(exc.value)


def test_corpus_hashes_cover_inline_docs_too():
    """A silently edited injection payload has to change the manifest exactly as a
    silently edited fixture file would."""
    from harness.cases import Case, ContextDoc

    case = Case(
        id="c", bucket="adversarial", input="q",
        context=(ContextDoc(id="planted", text="payload", tainted=True, canary="payload"),),
        checks=(), judge=(), why="w", source="constructed", added="2026-08-17",
    )
    hashes = records.corpus_hashes([case])
    assert "inline:c:planted" in hashes
    assert hashes["inline:c:planted"] == records.sha256_text("payload")


def test_partial_run_directory_is_identifiable(tmp_path):
    """A run that died mid-batch leaves outputs but no summary.json. That has to
    be distinguishable from a complete run, because the crash-survivable write
    path means a dead run leaves real files behind."""
    d = tmp_path / "run-x"
    d.mkdir()
    records.write_json(str(d / "manifest.json"), {"n_reruns": 5})
    rec = records.load_record(str(d))
    assert rec["summary"] == {}
    assert rec["results"] == []


def test_resolve_bare_names_stay_inside_runs(tmp_path):
    """A bare name is one component under runs/. '../x' used to resolve to
    runs/../x; a separator or a parent reference is a path, and a path that
    does not exist is not found."""
    import pytest
    (tmp_path / "run-x").mkdir()
    assert records.resolve("run-x", runs_dir=str(tmp_path)) == str(tmp_path / "run-x")
    with pytest.raises(FileNotFoundError):
        records.resolve("../run-x", runs_dir=str(tmp_path / "sub"))


def test_new_record_dir_allocation_is_atomic_under_a_race(tmp_path):
    """Two allocators for the same manifest in the same second both see seq 1
    absent; mkdir is the claim, so they get seq 1 and 2 instead of one of them
    dying on FileExistsError."""
    from concurrent.futures import ThreadPoolExecutor
    manifest = {"k": "v"}
    with ThreadPoolExecutor(max_workers=8) as pool:
        paths = list(pool.map(lambda _: records.new_record_dir("run", manifest, str(tmp_path)),
                              range(8)))
    assert len(set(paths)) == 8
