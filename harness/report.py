"""Report emitters.

Section order is the argument. The per-case table comes first because that is
where a regression is visible, the aggregates come second because that is where
one hides, and the "can you call it?" verdict comes last because it is what the
reader should leave with. A report that opened with "pass rate: 82% (+4)" would
be technically complete and would still get a bad change shipped.

Markdown into the record directory, aligned plain text to stdout, and nothing
else. No HTML, no dashboard. A dashboard is a thing people look at; a file
committed next to the code is a thing people diff.
"""

from __future__ import annotations


from harness import judge as judge_mod
from harness import stats
from harness.runner import case_state, pass_rate

def _isnan(x) -> bool:
    return isinstance(x, float) and x != x


BUCKET_ORDER = ("ordinary", "known_hard", "adversarial")
ARROW = {("pass", "fail"): "vv", ("pass", "flaky"): "v ", ("flaky", "fail"): "v ",
         ("fail", "pass"): "^^", ("flaky", "pass"): "^ ", ("fail", "flaky"): "^ "}
SEVERITY = {"pass": 2, "flaky": 1, "fail": 0}


def _table(rows: list[list[str]], headers: list[str]) -> str:
    widths = [len(h) for h in headers]
    for r in rows:
        for i, cell in enumerate(r):
            widths[i] = max(widths[i], len(cell))
    out = ["| " + " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers)) + " |"]
    out.append("|" + "|".join("-" * (w + 2) for w in widths) + "|")
    for r in rows:
        out.append("| " + " | ".join(c.ljust(widths[i]) for i, c in enumerate(r)) + " |")
    return "\n".join(out)


def run_report(record: dict) -> str:
    """Single-run report: per-bucket rates, flaky findings, per-check failures."""
    m, summary = record["manifest"], record["summary"]
    lines = [
        f"# {record['name']}",
        "",
        f"- prompt: `{m['prompt']['path']}` ({m['prompt']['sha256'][:19]})",
        f"- model: `{m['model']['requested']}` via `{m['model']['name']}` "
        f"(server reported `{m['model']['server_reported']}`)",
        f"- decoding: {m['decoding']}",
        f"- reruns per case: {m['n_reruns']}   cases: {m['n_cases']}",
        f"- harness: {m['harness_git_sha'][:12]}   started: {m['started']}",
    ]
    if m.get("closed_book"):
        lines.append("- **closed book**: fixtures withheld; this is the contamination probe.")
    lines += ["", "## Pass rate by bucket", ""]

    rows = []
    for bucket in BUCKET_ORDER:
        entries = [e for e in summary.values() if e["bucket"] == bucket]
        if not entries:
            continue
        strict = sum(1 for e in entries if case_state(e) == "pass")
        mean_p = sum(pass_rate(e) for e in entries) / len(entries)
        ci = stats.wilson(strict, len(entries))
        rows.append([bucket, f"{strict}/{len(entries)}", f"{strict/len(entries):.2f}",
                     str(ci), f"{mean_p:.3f}"])
    strict_all = sum(1 for e in summary.values() if case_state(e) == "pass")
    n_all = len(summary)
    if n_all:
        rows.append(["ALL", f"{strict_all}/{n_all}", f"{strict_all/n_all:.2f}",
                     str(stats.wilson(strict_all, n_all)),
                     f"{sum(pass_rate(e) for e in summary.values())/n_all:.3f}"])
    lines.append(_table(rows, ["bucket", "strict", "rate", "Wilson 95%", "mean p-hat"]))
    lines += [
        "",
        "Strict counts a case only when every rerun passed every check. The mean p-hat "
        "column uses the full rerun distribution, so the gap between the two columns is "
        "flakiness.",
        "",
    ]

    empties = {cid: e.get("empty", 0) for cid, e in summary.items() if e.get("empty")}
    total_empty = sum(empties.values())
    lines += ["## Empty generations", ""]
    if not total_empty:
        lines.append("None. Every rerun returned content.")
    else:
        planned = m["n_reruns"] * m["n_cases"]
        lines.append(
            f"**{total_empty} of {planned} generations came back empty** after retries and "
            "were dropped from scoring rather than counted as failures."
        )
        lines.append("")
        lines.append(_table(
            [[cid, summary[cid]["bucket"], f"{n}/{m['n_reruns']}",
              str(summary[cid]["conjunction"]["n"])]
             for cid, n in sorted(empties.items(), key=lambda kv: -kv[1])],
            ["case", "bucket", "empty", "reruns scored"],
        ))
        lines += [
            "",
            "An empty body is the model spending its whole token budget before it starts "
            "answering, not an answer. Scoring one would be worse than dropping it: an "
            "empty string fails must_refuse and passes must_not_cite and must_not_contain "
            "vacuously, so it reads as a refusal regression with evidence attached. The "
            "count is printed because dropping data quietly is its own dishonesty, and a "
            "case whose n shrank has a wider interval than its row suggests.",
        ]
        nodata = [cid for cid, e in summary.items() if case_state(e) == "nodata"]
        if nodata:
            lines += [
                "",
                f"**{len(nodata)} case(s) have no usable rerun at all** and are reported as "
                f"nodata rather than fail: {', '.join(sorted(nodata))}. Raise --max-tokens "
                "and rerun before reading anything into these.",
            ]
    lines.append("")

    flaky = [(cid, e) for cid, e in sorted(summary.items()) if case_state(e) == "flaky"]
    lines += ["## Flaky cases", ""]
    if not flaky:
        lines.append("None. Every case was all-pass or all-fail across its reruns.")
    else:
        frows = []
        for cid, e in flaky:
            conj = e["conjunction"]
            cp = stats.clopper_pearson(conj["passes"], conj["n"])
            unstable = [n for n, v in sorted(e["checks"].items()) if 0 < v["passes"] < v["n"]]
            frows.append([cid, e["bucket"], f"{conj['passes']}/{conj['n']}", str(cp),
                          ", ".join(unstable) or "(conjunction only)"])
        lines.append(_table(frows, ["case", "bucket", "k/n", "Clopper-Pearson 95%", "unstable checks"]))
        lines += [
            "",
            "Flaky is a finding, not a rounding error: either the check is too strict or "
            "the behavior is unstable. At this n the interval is wide enough that a 9/10 "
            "case is not distinguishable from a stable one, so read the interval before "
            "calling any single case unstable.",
        ]
    lines.append("")

    judged = judge_mod.outcomes(record)
    lines += ["## Judge verdicts", ""]
    if not judged:
        lines += [
            "No judge questions have been run against this record. "
            "`python -m harness judge <run>` fills this in.",
            "",
            "Nothing downstream treats that as a pass. The deterministic checks above are "
            "the whole result until it is filled in, which is the intended default: the "
            "judge is a second opinion on the cases that need one, not a prerequisite.",
        ]
    else:
        jrows = []
        for cid in sorted(judged):
            for qid, q in sorted(judged[cid].items()):
                jrows.append([
                    cid, qid, f"{q['passes']}/{q['n']}", f"{q['mean_p_pass']:.2f}",
                    str(q["split"]), str(q["unparseable"]),
                ])
        lines.append(_table(
            jrows, ["case", "question", "k/n", "mean p_pass", "split reruns", "unparseable"]
        ))
        lines += [
            "",
            "`mean p_pass` is the judge sampled five times per rerun, so 1.00 means it said "
            "the same thing every time and 0.60 means it did not. `split reruns` counts the "
            "reruns where it was not unanimous. A question that is always split is not "
            "measuring what its wording says it measures, whichever way the verdict lands.",
        ]
        stuck = sum(q["unparseable"] for c in judged.values() for q in c.values())
        if stuck:
            lines.append(
                f"\n**{stuck} judge sample(s) did not start with YES or NO** and were "
                "dropped. The protocol requires the verdict first, and a reply that buries "
                "it is not recovered by searching further into the text: that would put "
                "back exactly the rationalization the protocol removes."
            )
    lines.append("")

    lines += ["## Failing checks", ""]
    failing = {}
    for cid, e in summary.items():
        for name, v in e["checks"].items():
            if v["passes"] < v["n"]:
                failing.setdefault(name.split(":")[0], []).append(cid)
    if not failing:
        lines.append("None.")
    else:
        lines.append(_table(
            [[name, str(len(cids)), ", ".join(sorted(cids)[:4]) + ("..." if len(cids) > 4 else "")]
             for name, cids in sorted(failing.items(), key=lambda kv: -len(kv[1]))],
            ["check", "cases", "examples"],
        ))
    lines.append("")
    return "\n".join(lines)


def compare_report(rec_a: dict, rec_b: dict, flips: list[dict], st: dict) -> str:
    """A/B report. Per-case first, aggregates second, verdict last."""
    ma, mb = rec_a["manifest"], rec_b["manifest"]
    lines = [
        f"# {rec_a['name']}  ->  {rec_b['name']}",
        "",
        f"- A: `{ma['prompt']['path']}` ({ma['prompt']['sha256'][:19]})",
        f"- B: `{mb['prompt']['path']}` ({mb['prompt']['sha256'][:19]})",
        f"- model: `{ma['model']['server_reported']}` -> `{mb['model']['server_reported']}`",
        f"- reruns: {ma['n_reruns']} / {mb['n_reruns']}   cases: {len(flips)}",
        "",
        "## Per-case changes, regressions first",
        "",
    ]

    def sort_key(f):
        return (SEVERITY[f["state_b"]] - SEVERITY[f["state_a"]], f["delta"], f["bucket"], f["case_id"])

    rows = []
    for f in sorted(flips, key=sort_key):
        move = ARROW.get((f["state_a"], f["state_b"]), "  " if f["state_a"] == f["state_b"] else "??")
        rows.append([
            f["case_id"], f["bucket"], f["state_a"], move, f["state_b"],
            f"{f['k_a']}/{f['n_a']}", f"{f['k_b']}/{f['n_b']}", f"{f['delta']:+.2f}",
            ", ".join(f["checks_flipped"]) or "",
        ])
    lines.append(_table(rows, ["case", "bucket", "A", "", "B", "k/n A", "k/n B", "d p-hat", "checks flipped"]))
    if st.get("unpairable_cases"):
        lines += [
            "",
            f"**{len(st['unpairable_cases'])} case(s) excluded as unpairable**: "
            f"{', '.join(st['unpairable_cases'])}. Every rerun came back empty on one "
            "side or the other, so there is nothing to compare. They are named here "
            "rather than quietly dropped, because a comparison over a smaller set than "
            "the reader thinks is the same error as a comparison over a different one.",
        ]
    if st.get("empty_a") or st.get("empty_b"):
        lines.append(
            f"\nEmpty generations dropped from scoring: {st.get('empty_a', 0)} in A, "
            f"{st.get('empty_b', 0)} in B. Cases with a shrunken n carry more uncertainty "
            "than their row shows."
        )
    changed = [f for f in flips if f["state_a"] != f["state_b"]]
    lines += [
        "",
        f"{len(changed)} of {len(flips)} cases changed state. Unchanged rows are included "
        "on purpose: a comparison that prints only what moved cannot be checked against "
        "the one that did not.",
        "",
        "## Per-bucket totals",
        "",
    ]

    brows = []
    for bucket in BUCKET_ORDER + ("ALL",):
        sub = flips if bucket == "ALL" else [f for f in flips if f["bucket"] == bucket]
        if not sub:
            continue
        pa = sum(1 for f in sub if f["state_a"] == "pass")
        pb = sum(1 for f in sub if f["state_b"] == "pass")
        s = st["buckets"][bucket]
        brows.append([
            bucket, f"{pa}/{len(sub)}", str(stats.wilson(pa, len(sub))),
            f"{pb}/{len(sub)}", str(stats.wilson(pb, len(sub))),
            f"{s['b']}/{s['c']}", f"{s['p']:.4f}",
        ])
    lines.append(_table(brows, ["bucket", "A strict", "Wilson A", "B strict", "Wilson B", "b/c", "McNemar p"]))
    lines += [
        "",
        "b = passed under A and failed under B. c = the reverse. Concordant cases carry no "
        "information about the difference and are not in the test.",
        "",
        "## Can you call it?",
        "",
    ]

    agg = st["buckets"]["ALL"]
    lines += [
        f"- discordant pairs: b={agg['b']} (A pass, B fail), c={agg['c']} (A fail, B pass)",
        f"- exact McNemar ({agg['variant']}): p = {agg['p']:.4f}",
        f"- paired bootstrap on per-case p-hat: delta = {st['bootstrap']['observed']:+.4f}, "
        f"95% CI {st['bootstrap']['ci']} "
        f"(B={st['bootstrap']['iterations']}, seed={st['bootstrap']['seed']})",
    ]
    floor = st.get("noise_floor")
    if floor and floor.get("splits"):
        lines.append(
            f"- A/A noise floor from {floor['splits']} random half-splits of A's own reruns: "
            f"95th percentile |delta| = {floor['p95_mean_delta']:.4f}"
        )
    else:
        lines.append(
            "- A/A noise floor: not computed. It needs at least 4 reruns per case in arm A; "
            "with fewer, a half-split has nothing left to compare."
        )
    lines += ["", "**" + st["verdict"] + "**", ""]

    j = st.get("judge") or {}
    lines += ["## Judge outcome, reported separately", ""]
    if not j.get("n"):
        lines += [
            "Neither record has judge verdicts, or no case has them on both sides. "
            "The deterministic result above stands on its own.",
            "",
        ]
    else:
        lines.append(_table(
            [[c["case_id"], c["a"], "->", c["b"]] for c in j["cases"]],
            ["case", "A", "", "B"],
        ))
        lines += [
            "",
            f"{j['n']} case(s) judged on both sides. b={j['b']}, c={j['c']}, "
            f"exact McNemar p = {j['p']:.4f} "
            f"(smallest achievable at this discordance: {j['min_achievable_p']:.4f}).",
            "",
            "This is a second outcome, not a component of the first. Nothing above changes "
            "because of it. Folding a judge verdict into the pass/fail number would let a "
            "model's opinion gate a result the rubric says it may only flag, and it would do "
            "so without showing up anywhere a reader would look.",
            "",
        ]


    lines += [
        "### What this comparison can and cannot detect",
        "",
        f"- cases: {len(flips)}; discordance observed: {st['psi']:.2f}",
        (
            "- minimum detectable effect at this n and discordance, exact test, 80% power: "
            "**no effect is detectable at all**. No delta reaches 80% power on this many "
            "cases, so the exact test is decorative here and the bootstrap plus the noise "
            "floor are the only views carrying information."
            if _isnan(st["mde"])
            else f"- minimum detectable effect at this n and discordance, exact test, 80% "
                 f"power: {st['mde']:.2f} absolute on the strict binary outcome"
        ),
        f"- smallest two-sided p the exact test can produce at {st['buckets']['ALL']['b'] + st['buckets']['ALL']['c']} "
        f"discordant pair(s): {st.get('min_achievable_p', float('nan')):.4f}",
        "",
        "An effect smaller than the detectable minimum is not something this set can "
        "distinguish from noise, whatever the point estimate says. That is a property of the "
        "sample size, and it is printed here rather than left for the reader to work out, "
        "because the alternative is a report that implies it can bless a three-point "
        "improvement. The second line is the one people misread: when the smallest achievable "
        "p sits above 0.05, a non-significant result is not a finding about the prompt.",
        "",
    ]
    return "\n".join(lines)


def to_plain(markdown: str) -> str:
    """Markdown to stdout: strip the emphasis, keep the tables."""
    out = []
    for line in markdown.splitlines():
        if line.startswith("#"):
            text = line.lstrip("#").strip()
            out += ["", text, "-" * len(text)]
        else:
            out.append(line.replace("**", ""))
    return "\n".join(out).strip() + "\n"
