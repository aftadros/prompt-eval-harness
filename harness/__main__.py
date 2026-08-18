"""Command line. argparse, because a dependency to parse six subcommands would be
the exact ceremony this repo argues against.

    python -m harness run       --prompt prompts/v2.txt [--n 5] [--model local]
    python -m harness compare   <run-a> <run-b>
    python -m harness judge     <run> [--judge local]
    python -m harness label     <run> [--question grounded]
    python -m harness calibrate <run> [<run>...]
    python -m harness judge-audit [--judge local]
    python -m harness report    <record-dir>
    python -m harness validate
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harness import judge as judge_mod  # noqa: E402
from harness import model as model_mod  # noqa: E402
from harness import records, report, stats  # noqa: E402
from harness.cases import CaseError, load_all  # noqa: E402
from harness.runner import RunConfig, case_state, pass_rate, run  # noqa: E402


# ----------------------------------------------------------------- compare


def build_flips(rec_a: dict, rec_b: dict) -> list[dict]:
    sa, sb = rec_a["summary"], rec_b["summary"]
    shared = sorted(set(sa) & set(sb))
    flips = []
    for cid in shared:
        ea, eb = sa[cid], sb[cid]
        checks_flipped = []
        for name in sorted(set(ea["checks"]) | set(eb["checks"])):
            va = ea["checks"].get(name, {"passes": 0, "n": 0})
            vb = eb["checks"].get(name, {"passes": 0, "n": 0})
            ra = va["passes"] / va["n"] if va["n"] else 0.0
            rb = vb["passes"] / vb["n"] if vb["n"] else 0.0
            if ra != rb:
                checks_flipped.append(f"{name.split(':')[0]} {va['passes']}/{va['n']}->{vb['passes']}/{vb['n']}")
        flips.append({
            "case_id": cid,
            "bucket": ea["bucket"],
            "state_a": case_state(ea),
            "state_b": case_state(eb),
            "k_a": ea["conjunction"]["passes"], "n_a": ea["conjunction"]["n"],
            "k_b": eb["conjunction"]["passes"], "n_b": eb["conjunction"]["n"],
            "delta": pass_rate(eb) - pass_rate(ea),
            "checks_flipped": checks_flipped,
        })
    return flips


def compare_stats(rec_a: dict, rec_b: dict, flips: list[dict]) -> dict:
    buckets: dict[str, dict] = {}
    for bucket in ("ordinary", "known_hard", "adversarial", "ALL"):
        sub = flips if bucket == "ALL" else [f for f in flips if f["bucket"] == bucket]
        if not sub:
            continue
        b = sum(1 for f in sub if f["state_a"] == "pass" and f["state_b"] != "pass")
        c = sum(1 for f in sub if f["state_a"] != "pass" and f["state_b"] == "pass")
        mc = stats.mcnemar_exact(b, c)
        buckets[bucket] = {"b": b, "c": c, "p": mc.p, "variant": mc.variant, "n": len(sub)}

    pa = [f["k_a"] / f["n_a"] if f["n_a"] else 0.0 for f in flips]
    pb = [f["k_b"] / f["n_b"] if f["n_b"] else 0.0 for f in flips]
    observed, ci = stats.paired_bootstrap_delta(pa, pb)

    per_case_a = []
    for cid in sorted(rec_a["summary"]):
        rows = [r for r in rec_a["results"] if r["case_id"] == cid]
        per_case_a.append([bool(r["all_passed"]) for r in sorted(rows, key=lambda r: r["rerun"])])
    floor = stats.aa_noise_floor(per_case_a) if per_case_a and len(per_case_a[0]) >= 4 else None

    agg = buckets.get("ALL", {"b": 0, "c": 0, "p": 1.0})
    n = len(flips)
    psi = (agg["b"] + agg["c"]) / n if n else 0.0
    mde = stats.find_mde(n, max(psi, 0.05), sims=800) if n else float("nan")

    verdict = _verdict(agg, observed, ci, floor, mde)
    return {
        "buckets": buckets,
        "bootstrap": {
            "observed": observed, "ci": str(ci),
            "iterations": stats.DEFAULT_B, "seed": stats.DEFAULT_SEED,
        },
        "noise_floor": floor,
        "psi": psi,
        "mde": mde,
        "verdict": verdict,
    }


def _verdict(agg: dict, observed: float, ci, floor, mde: float) -> str:
    """The blunt sentence. Templated on purpose: a verdict written fresh each
    time is a verdict that drifts toward whatever the author hoped for."""
    straddles = ci.lo <= 0 <= ci.hi
    sig = agg["p"] <= 0.05
    inside_floor = floor and abs(observed) <= floor["p95_mean_delta"]
    if inside_floor:
        return (
            f"NOT distinguishable from rerun noise. The observed delta ({observed:+.3f}) is "
            f"inside the A/A noise floor ({floor['p95_mean_delta']:.3f}), which is what running "
            "the same prompt twice looks like on this rig. Do not ship on this delta."
        )
    if not sig and straddles:
        return (
            f"CANNOT BE CALLED at this sample size. McNemar p = {agg['p']:.4f} and the bootstrap "
            f"interval {ci} straddles zero. With {agg['b'] + agg['c']} discordant pairs the test "
            f"cannot resolve an effect below about {mde:.2f}. This is not evidence of no effect; "
            "it is an absence of evidence either way. Do not ship on this delta."
        )
    if sig and not straddles:
        direction = "improvement" if observed > 0 else "regression"
        return (
            f"A {direction} that survives the test: McNemar p = {agg['p']:.4f}, bootstrap "
            f"{ci} excludes zero. Read the per-case table before acting on it, and check the "
            "correction family in METRICS.md before calling it significant."
        )
    return (
        f"MIXED. McNemar p = {agg['p']:.4f}, bootstrap {ci}. The two views of the same data "
        "disagree, which usually means the effect sits near this set's resolution limit "
        f"(about {mde:.2f}). Treat it as uncalled."
    )


# ----------------------------------------------------------------- commands


def cmd_run(args) -> int:
    cases = load_all()
    cfg = RunConfig(
        prompt_path=args.prompt,
        model_name=args.model,
        n_reruns=args.n,
        buckets=tuple(args.buckets or ()),
        case_ids=tuple(args.case or ()),
        decoding=model_mod.Decoding(
            temperature=args.temperature, top_p=args.top_p,
            max_tokens=args.max_tokens, seed=args.seed,
        ),
        closed_book=args.closed_book,
        concurrency=args.concurrency,
    )
    path = run(cases, cfg)
    rec = records.load_record(path)
    md = report.run_report(rec)
    records.write_report(os.path.join(path, "report.md"), md)
    print(report.to_plain(md))
    print(f"record: {os.path.relpath(path, records.REPO_ROOT)}")
    return 0


def cmd_compare(args) -> int:
    rec_a = records.load_record(records.resolve(args.run_a))
    rec_b = records.load_record(records.resolve(args.run_b))
    for key in ("cases", "corpus"):
        if rec_a["manifest"][key] != rec_b["manifest"][key]:
            print(
                f"refusing to compare: the {key} hashes differ between these runs.\n"
                "Paired statistics require the same paired cases. Comparing runs over "
                "different case sets produces a number, and the number means nothing.",
                file=sys.stderr,
            )
            return 2
    flips = build_flips(rec_a, rec_b)
    st = compare_stats(rec_a, rec_b, flips)
    manifest = {
        "run_a": rec_a["name"], "run_b": rec_b["name"],
        "cases": rec_a["manifest"]["cases"], "corpus": rec_a["manifest"]["corpus"],
        "n_cases": len(flips),
    }
    out_dir = records.new_record_dir("cmp", manifest)
    records.write_json(os.path.join(out_dir, "compare.json"), manifest)
    for f in flips:
        records.append_jsonl(os.path.join(out_dir, "flips.jsonl"), f)
    records.write_json(os.path.join(out_dir, "stats.json"), st)
    md = report.compare_report(rec_a, rec_b, flips, st)
    records.write_report(os.path.join(out_dir, "report.md"), md)
    print(report.to_plain(md))
    print(f"record: {os.path.relpath(out_dir, records.REPO_ROOT)}")
    return 0


def cmd_judge(args) -> int:
    path = records.resolve(args.run)
    rows = judge_mod.run_judge(path, judge_model=args.judge, samples=args.samples)
    print(f"{len(rows)} judge verdict(s) written to {os.path.join(path, 'judge.jsonl')}")
    return 0


def cmd_label(args) -> int:
    """Blinded labeling. Outputs shuffled and identified by hash only.

    Blind to model and prompt identity and blind to the judge's verdict, because
    a label collected after seeing either is a label about the judge. Bucket is
    not blinded: adversarial questions announce themselves, and pretending
    otherwise would be theater rather than blinding.
    """
    path = records.resolve(args.run)
    rec = records.load_record(path)
    cases = {c.id: c for c in load_all()}
    labels_path = os.path.join(records.REPO_ROOT, "labels", "human-labels.jsonl")
    done = {(r["output_sha"], r["question_id"]) for r in records.read_jsonl(labels_path)}

    items = []
    for r in rec["results"]:
        case = cases.get(r["case_id"])
        if not case or not case.judge:
            continue
        for qid in case.judge:
            if args.question and qid != args.question:
                continue
            if (r["output_sha"], qid) in done:
                continue
            items.append((r, case, qid))
    random.Random(args.shuffle_seed).shuffle(items)
    if not items:
        print("nothing left to label in this run.")
        return 0

    questions = judge_mod.load_questions()
    print(f"{len(items)} item(s) to label. Ctrl-C to stop; progress is appended as you go.\n")
    for i, (r, case, qid) in enumerate(items, 1):
        answer = open(
            os.path.join(path, "outputs", case.id, f"r{r['rerun']}.txt"), encoding="utf-8"
        ).read()
        print("=" * 78)
        print(f"[{i}/{len(items)}]  bucket: {case.bucket}   output: {r['output_sha'][:19]}")
        print("-" * 78)
        print("SOURCE:\n" + case.context_text()[:2500])
        print("-" * 78)
        print("QUESTION ASKED:\n" + case.input)
        print("-" * 78)
        print("ANSWER:\n" + answer)
        print("-" * 78)
        print("YOUR QUESTION: " + questions[qid]["question"].strip())
        print(f"(pass when: {questions[qid]['pass_when']})")
        try:
            raw = input("y / n / s(kip) / q(uit) > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nstopped.")
            return 0
        if raw in ("q", "quit"):
            return 0
        if raw in ("s", "skip", ""):
            continue
        note = input("note (optional) > ").strip()
        records.append_jsonl(labels_path, {
            "output_sha": r["output_sha"], "case_id": case.id, "bucket": case.bucket,
            "question_id": qid, "human_verdict": "pass" if raw.startswith("y") else "fail",
            "labeler": args.labeler, "note": note,
        })
    print("done.")
    return 0


def cmd_calibrate(args) -> int:
    labels_path = os.path.join(records.REPO_ROOT, "labels", "human-labels.jsonl")
    labels = {(r["output_sha"], r["question_id"]): r for r in records.read_jsonl(labels_path)}
    if not labels:
        print(
            "no human labels yet. `python -m harness label <run>` first.\n"
            "Calibration without labels is the step everyone skips, and skipping it is "
            "what makes a judge a number generator.",
            file=sys.stderr,
        )
        return 2

    joined = []
    for run_arg in args.runs:
        rec = records.load_record(records.resolve(run_arg))
        for row in rec["judge"]:
            key = (row["output_sha"], row["question_id"])
            if key in labels:
                joined.append({
                    "output_sha": row["output_sha"], "question_id": row["question_id"],
                    "case_id": row["case_id"], "bucket": row["bucket"],
                    "judge_p_pass": row["p_pass"], "judge_verdict": row["verdict"],
                    "human_verdict": labels[key]["human_verdict"],
                })
    if not joined:
        print("no (output, question) pairs are both judged and labeled.", file=sys.stderr)
        return 2

    j = [x["judge_verdict"] == "pass" for x in joined]
    h = [x["human_verdict"] == "pass" for x in joined]
    ag = stats.cohens_kappa(j, h)
    ci = stats.kappa_bootstrap_ci(j, h)

    bins = {"unanimous": [], "strong": [], "split": []}
    for x in joined:
        conf = max(x["judge_p_pass"], 1 - x["judge_p_pass"])
        name = "unanimous" if conf >= 0.999 else ("strong" if conf >= 0.8 else "split")
        bins[name].append(x["judge_verdict"] == x["human_verdict"])
    bin_stats = {
        k: {"n": len(v), "accuracy": (sum(v) / len(v)) if v else None,
            "ci": str(stats.wilson(sum(v), len(v))) if v else None}
        for k, v in bins.items()
    }
    pi = sum(h) / len(h)
    out = {
        "n": ag.n, "raw_agreement": ag.raw, "kappa": ag.kappa, "kappa_ci": str(ci),
        "pabak": ag.pabak, "confusion": ag.confusion, "human_pass_rate": pi,
        "kappa_implied_by_80pct_at_this_base_rate": stats.kappa_at(0.80, pi)[1],
        "consistency_bins": bin_stats,
        "honesty": (
            "Kappa at this n supports coarse bands only. Credibly-above-0.4 and "
            "credibly-below-0.6 are claimable; 0.65 versus 0.72 is not. Single rater, "
            "so this is judge-versus-one-human agreement and says nothing about "
            "human-human reliability."
        ),
    }
    manifest = {"runs": [records.load_record(records.resolve(r))["name"] for r in args.runs],
                "labels_sha": records.sha256_file(labels_path), "n_joined": len(joined)}
    out_dir = records.new_record_dir("cal", manifest)
    records.write_json(os.path.join(out_dir, "inputs.json"), manifest)
    for row in joined:
        records.append_jsonl(os.path.join(out_dir, "joined.jsonl"), row)
    records.write_json(os.path.join(out_dir, "stats.json"), out)
    print(json.dumps(out, indent=2))
    print(f"\nrecord: {os.path.relpath(out_dir, records.REPO_ROOT)}")
    return 0


def cmd_judge_audit(args) -> int:
    print(json.dumps(judge_mod.audit(judge_model=args.judge, samples=args.samples), indent=2))
    return 0


def cmd_report(args) -> int:
    path = records.resolve(args.record)
    rec = records.load_record(path)
    if os.path.exists(os.path.join(path, "compare.json")):
        info = json.load(open(os.path.join(path, "compare.json")))
        rec_a = records.load_record(records.resolve(info["run_a"]))
        rec_b = records.load_record(records.resolve(info["run_b"]))
        flips = records.read_jsonl(os.path.join(path, "flips.jsonl"))
        st = json.load(open(os.path.join(path, "stats.json")))
        md = report.compare_report(rec_a, rec_b, flips, st)
    else:
        md = report.run_report(rec)
    records.write_report(os.path.join(path, "report.md"), md)
    print(report.to_plain(md))
    return 0


def cmd_validate(args) -> int:
    """Load and check the whole set without making a single model call."""
    try:
        cases = load_all()
    except CaseError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    from collections import Counter

    counts = Counter(c.bucket for c in cases)
    posts = set()
    per_post_buckets: dict[str, set] = {}
    for c in cases:
        for d in c.context:
            if d.path and "fixtures" in d.path:
                slug = d.id.split("--")[0]
                posts.add(slug)
                per_post_buckets.setdefault(slug, set()).add(c.bucket)
    print(f"{len(cases)} cases: " + ", ".join(f"{k}={counts[k]}" for k in sorted(counts)))
    print(f"judge-routed: {sum(1 for c in cases if c.judge)}")
    print(f"posts referenced: {len(posts)}")
    gaps = [p for p, b in sorted(per_post_buckets.items()) if "ordinary" not in b or len(b) < 2]
    if gaps:
        print("coverage quota not met (needs >=1 ordinary and >=1 other bucket):")
        for p in gaps:
            print(f"  {p}: {sorted(per_post_buckets[p])}")
        return 1
    print("coverage quota met: every post appears in an ordinary case and at least one other bucket.")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="harness", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run the golden set through a prompt")
    r.add_argument("--prompt", default="prompts/v1.txt")
    r.add_argument("--model", default="local")
    r.add_argument("--n", type=int, default=5, help="reruns per case")
    r.add_argument("--buckets", nargs="*", choices=["ordinary", "known_hard", "adversarial"])
    r.add_argument("--case", nargs="*", help="restrict to specific case ids")
    r.add_argument("--temperature", type=float, default=0.7)
    r.add_argument("--top-p", dest="top_p", type=float, default=0.95)
    r.add_argument("--max-tokens", dest="max_tokens", type=int, default=1024)
    r.add_argument("--seed", type=int, default=None)
    r.add_argument("--concurrency", type=int, default=1)
    r.add_argument("--closed-book", action="store_true",
                   help="withhold fixtures: the contamination probe")
    r.set_defaults(func=cmd_run)

    c = sub.add_parser("compare", help="A/B two runs")
    c.add_argument("run_a")
    c.add_argument("run_b")
    c.set_defaults(func=cmd_compare)

    j = sub.add_parser("judge", help="run judge questions over a run's outputs")
    j.add_argument("run")
    j.add_argument("--judge", default="local")
    j.add_argument("--samples", type=int, default=5)
    j.set_defaults(func=cmd_judge)

    lb = sub.add_parser("label", help="blinded human labeling")
    lb.add_argument("run")
    lb.add_argument("--question", default=None)
    lb.add_argument("--labeler", default="anthony")
    lb.add_argument("--shuffle-seed", type=int, default=stats.DEFAULT_SEED)
    lb.set_defaults(func=cmd_label)

    cal = sub.add_parser("calibrate", help="judge vs human agreement")
    cal.add_argument("runs", nargs="+")
    cal.set_defaults(func=cmd_calibrate)

    ja = sub.add_parser("judge-audit", help="run the bias probes")
    ja.add_argument("--judge", default="local")
    ja.add_argument("--samples", type=int, default=5)
    ja.set_defaults(func=cmd_judge_audit)

    rp = sub.add_parser("report", help="regenerate report.md for a record")
    rp.add_argument("record")
    rp.set_defaults(func=cmd_report)

    v = sub.add_parser("validate", help="load and check the case set, no model calls")
    v.set_defaults(func=cmd_validate)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
