"""The run loop.

Every case, N times, through the checks, into a record. The only subtlety is that
N is not 1 and the results are stored as a distribution rather than a verdict.

A case that passes 3 times out of 5 is not a passing case and it is not a failing
case. It is a flaky case, which is a finding in its own right: either the check is
too strict or the behavior really is unstable, and both are worth knowing before
a number moves and nobody can say why. Collapsing k/n to a boolean at write time
throws that away permanently, so `summary.json` stores k and n and every consumer
derives what it needs.
"""

from __future__ import annotations

import concurrent.futures as futures
import os
import sys
import threading
import time
from dataclasses import dataclass

import checks as checks_pkg
from harness import model as model_mod
from harness import records
from harness.cases import Case

REPO_ROOT = records.REPO_ROOT

USER_TEMPLATE = """Reference material:

{context}

Question: {question}"""


@dataclass
class RunConfig:
    prompt_path: str
    model_name: str = "local"
    n_reruns: int = 5
    buckets: tuple[str, ...] = ()
    case_ids: tuple[str, ...] = ()
    decoding: model_mod.Decoding = model_mod.Decoding()
    #: Drop the retrieval fixtures and tell the model to answer from its own
    #: knowledge. This is the contamination probe, not a normal run: the same
    #: questions and the same checks against a model with nothing to ground in.
    closed_book: bool = False
    #: In-flight requests. Purely a wall-clock lever: results are buffered and
    #: written in a fixed order regardless, so a run at concurrency 8 and the same
    #: run at concurrency 1 produce byte-identical `results.jsonl` given the same
    #: outputs.
    #:
    #: A local server batches these, and the return is real but far smaller than
    #: the request count suggests, because per-request latency grows as the batch
    #: does. Measured on one local 27B model: one call at a time ran 1.5 calls a
    #: minute, six at a time ran 3.3, and twelve at a time pushed per-request
    #: latency past the adapter's timeout (model.DEFAULT_TIMEOUT), so the run failed rather
    #: than merely slowed. Measure your own rig instead of trusting any of those
    #: numbers, and leave this at 1 against a shared endpoint, where the capacity
    #: is somebody else's.
    concurrency: int = 1


CLOSED_BOOK_NOTE = (
    "No reference material is available for this question. "
    "Answer from your own knowledge."
)


def select(cases: list[Case], cfg: RunConfig) -> list[Case]:
    out = cases
    if cfg.buckets:
        out = [c for c in out if c.bucket in cfg.buckets]
    if cfg.case_ids:
        wanted = set(cfg.case_ids)
        out = [c for c in out if c.id in wanted]
        missing = wanted - {c.id for c in out}
        if missing:
            raise SystemExit(f"no such case(s): {sorted(missing)}")
    if not out:
        raise SystemExit("selection matched no cases")
    return out


def build_user_message(case: Case, closed_book: bool) -> str:
    context = CLOSED_BOOK_NOTE if closed_book else case.context_text()
    return USER_TEMPLATE.format(context=context, question=case.input)


def run_checks(output: str, case: Case) -> list[checks_pkg.CheckResult]:
    results = []
    for name, params in case.checks:
        fn = checks_pkg.REGISTRY[name]
        results.append(fn(output, case, params))
    return results


def run(cases: list[Case], cfg: RunConfig, *, quiet: bool = False) -> str:
    """Execute a run and return the record directory."""
    selected = select(cases, cfg)
    config = model_mod.load_config()
    entry = config["models"][cfg.model_name]
    mdl = model_mod.build(cfg.model_name, config)
    server_reported = mdl.preflight()

    system = open(os.path.join(REPO_ROOT, cfg.prompt_path), encoding="utf-8").read()

    manifest = records.build_manifest(
        prompt_path=cfg.prompt_path,
        cases=selected,
        model_entry=entry,
        model_name=cfg.model_name,
        server_reported=server_reported,
        decoding=cfg.decoding,
        n_reruns=cfg.n_reruns,
        judge_info=None,
    )
    manifest["closed_book"] = cfg.closed_book
    record_dir = records.new_record_dir("run", manifest)
    records.write_json(os.path.join(record_dir, "manifest.json"), manifest)
    records.write_text(os.path.join(record_dir, "prompt.txt"), system)

    results_path = os.path.join(record_dir, "results.jsonl")
    started = time.time()
    total = len(selected) * cfg.n_reruns
    tasks = [(case, rerun) for case in selected for rerun in range(cfg.n_reruns)]
    outputs: dict[tuple[str, int], object] = {}
    progress = {"done": 0}
    lock = threading.Lock()

    def do(task):
        case, rerun = task
        completion = model_mod.complete_with_content(
            mdl, system, build_user_message(case, cfg.closed_book), cfg.decoding
        )
        # Written the moment it arrives, to its own path, so a crash at call 249
        # of 250 costs one call rather than the whole batch. The ordered pass
        # below reads them back; nothing here depends on completion order.
        records.write_text(
            os.path.join(record_dir, "outputs", case.id, f"r{rerun}.txt"), completion.text
        )
        with lock:
            progress["done"] += 1
            done = progress["done"]
            if not quiet:
                rate = done / max(1e-9, time.time() - started)
                print(
                    f"\r  {done}/{total}  {case.id:<30} r{rerun}  "
                    f"{rate*60:5.1f}/min  eta {(total-done)/max(1e-9,rate)/60:5.1f}m   ",
                    end="",
                    file=sys.stderr,
                    flush=True,
                )
        return (case.id, rerun), completion

    if cfg.concurrency > 1:
        with futures.ThreadPoolExecutor(max_workers=cfg.concurrency) as pool:
            for key, completion in pool.map(do, tasks):
                outputs[key] = completion
    else:
        for task in tasks:
            key, completion = do(task)
            outputs[key] = completion

    # Written in case order, then rerun order, so the record does not depend on
    # the order requests happened to finish in.
    summary: dict[str, dict] = {}
    for case in selected:
        case_summary = {
            "bucket": case.bucket,
            "n": cfg.n_reruns,
            "checks": {},
            "judge_questions": list(case.judge),
            "conjunction": {"passes": 0, "n": 0},
            "empty": 0,
        }
        for rerun in range(cfg.n_reruns):
            completion = outputs[(case.id, rerun)]
            if completion.is_empty:
                # Missing data, not a result. It lowers n rather than counting as
                # a fail, and the report prints the count so a shrunken n is
                # never silent.
                case_summary["empty"] += 1
                records.append_jsonl(
                    results_path,
                    {
                        "case_id": case.id,
                        "bucket": case.bucket,
                        "rerun": rerun,
                        "output_sha": records.sha256_text(completion.text),
                        "output_chars": 0,
                        "model_reported": completion.model_reported,
                        "usage": completion.usage,
                        "checks": [],
                        "empty": True,
                        "all_passed": None,
                    },
                )
                continue
            check_results = run_checks(completion.text, case)
            records.append_jsonl(
                results_path,
                {
                    "case_id": case.id,
                    "bucket": case.bucket,
                    "rerun": rerun,
                    "output_sha": records.sha256_text(completion.text),
                    "output_chars": len(completion.text),
                    "model_reported": completion.model_reported,
                    "usage": completion.usage,
                    "checks": [
                        {"name": r.name, "passed": r.passed, "evidence": r.evidence}
                        for r in check_results
                    ],
                    "empty": False,
                    "all_passed": all(r.passed for r in check_results),
                },
            )
            for r in check_results:
                slot = case_summary["checks"].setdefault(r.name, {"passes": 0, "n": 0})
                slot["n"] += 1
                slot["passes"] += 1 if r.passed else 0
            case_summary["conjunction"]["n"] += 1
            case_summary["conjunction"]["passes"] += 1 if all(r.passed for r in check_results) else 0
        summary[case.id] = case_summary

    if not quiet:
        print(file=sys.stderr)
    records.write_json(os.path.join(record_dir, "summary.json"), summary)
    return record_dir


def case_state(entry: dict) -> str:
    """Three-valued case state from the stored distribution.

    pass = every rerun passed every check, fail = none did, flaky = in between.
    Three values rather than two because "a change that converted passes into
    flaky" is its own regression class, and a boolean cannot express it.
    """
    conj = entry.get("conjunction", {"passes": 0, "n": 0})
    k, n = conj["passes"], conj["n"]
    if n == 0:
        # Every rerun came back empty, so there is no evidence either way. This
        # is deliberately not "fail": a case with no data and a case that failed
        # look identical on a report that has only three states, and the first
        # one is a broken rig while the second is a broken prompt.
        return "nodata"
    if k == n:
        return "pass"
    if k == 0:
        return "fail"
    return "flaky"


def pass_rate(entry: dict) -> float:
    conj = entry.get("conjunction", {"passes": 0, "n": 0})
    return conj["passes"] / conj["n"] if conj["n"] else 0.0
