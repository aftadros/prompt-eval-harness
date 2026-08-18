"""Model-graded checks, kept in one place so the judgment surface is visible.

Two things here are non-negotiable and both are about not fooling yourself.

The judge is sampled m times rather than asked once, so a verdict is a
distribution and "5-0 pass" and "3-2 pass" stay distinguishable. Collapsing them
at the point of measurement throws away the only cheap signal about whether to
trust the verdict, and it is the signal the calibration report is built from.

Pairwise judging always runs the order-swapped twin. A pair judged in one order
is a measurement of the judge's position preference as much as of the outputs,
and averaging over the swap would hide exactly the bias the swap exists to find.
A disagreement between the two orders is recorded as an event, never averaged
away.
"""

from __future__ import annotations

import os
import re

import yaml

from harness import model as model_mod
from harness import records

REPO_ROOT = records.REPO_ROOT
JUDGE_DIR = os.path.join(REPO_ROOT, "judge")

VERDICT_RE = re.compile(r"^\s*(YES|NO)\b", re.IGNORECASE)


def load_questions() -> dict[str, dict]:
    path = os.path.join(JUDGE_DIR, "questions.yaml")
    return {q["id"]: q for q in (yaml.safe_load(open(path, encoding="utf-8")) or [])}


def load_prompt_template() -> str:
    return open(os.path.join(JUDGE_DIR, "prompt.txt"), encoding="utf-8").read()


def judge_shas() -> dict[str, str]:
    return {
        "questions_sha": records.sha256_file(os.path.join(JUDGE_DIR, "questions.yaml")),
        "prompt_sha": records.sha256_file(os.path.join(JUDGE_DIR, "prompt.txt")),
    }


def parse_verdict(text: str) -> str | None:
    """First token or nothing.

    A judge that ignored the verdict-first instruction is not a judge whose
    answer should be recovered by searching further into the text: the protocol
    exists so a verdict is not a summary of an essay, and salvaging one from
    paragraph two silently reintroduces what the protocol removed. An unparseable
    reply is recorded as unparseable.
    """
    m = VERDICT_RE.match(text or "")
    return m.group(1).upper() if m else None


def render(template: str, *, source: str, question_input: str, answer: str, question: str) -> str:
    return (
        template.replace("{source}", source)
        .replace("{input}", question_input)
        .replace("{answer}", answer)
        .replace("{question}", question)
    )


def judge_one(
    mdl,
    template: str,
    question: dict,
    *,
    source: str,
    question_input: str,
    answer: str,
    samples: int = 5,
    decoding: model_mod.Decoding | None = None,
) -> dict:
    """Ask one question m times. Returns the distribution, not a verdict."""
    decoding = decoding or model_mod.Decoding(temperature=0.7, max_tokens=200)
    prompt = render(
        template,
        source=source,
        question_input=question_input,
        answer=answer,
        question=question["question"].strip(),
    )
    raw_samples, rationales = [], []
    for _ in range(samples):
        completion = mdl.complete("You are a careful grader.", prompt, decoding)
        v = parse_verdict(completion.text)
        raw_samples.append(v or "UNPARSEABLE")
        rationales.append(completion.text.strip()[:300])
    want = question["pass_when"].strip().upper()
    parseable = [s for s in raw_samples if s in ("YES", "NO")]
    passes = sum(1 for s in parseable if s == want)
    p_pass = passes / len(parseable) if parseable else 0.0
    return {
        "question_id": question["id"],
        "samples": raw_samples,
        "n_unparseable": len(raw_samples) - len(parseable),
        "p_pass": p_pass,
        "verdict": "pass" if p_pass > 0.5 else "fail",
        "rationale_first": rationales[0] if rationales else "",
    }


def run_judge(record_dir: str, judge_model: str = "local", samples: int = 5, quiet: bool = False):
    """Judge every judge-routed output in a run, appending to judge.jsonl."""
    from harness.cases import load_all

    record = records.load_record(record_dir)
    cases = {c.id: c for c in load_all()}
    questions = load_questions()
    template = load_prompt_template()
    mdl = model_mod.build(judge_model)
    mdl.preflight()
    shas = judge_shas()
    out_path = os.path.join(record_dir, "judge.jsonl")
    already = {
        (r["case_id"], r["rerun"], r["question_id"]) for r in records.read_jsonl(out_path)
    }

    rows = []
    for result in record["results"]:
        case = cases.get(result["case_id"])
        if case is None or not case.judge:
            continue
        answer_path = os.path.join(
            record_dir, "outputs", case.id, f"r{result['rerun']}.txt"
        )
        answer = open(answer_path, encoding="utf-8").read()
        for qid in case.judge:
            if (case.id, result["rerun"], qid) in already:
                continue
            verdict = judge_one(
                mdl,
                template,
                questions[qid],
                source=case.context_text(),
                question_input=case.input,
                answer=answer,
                samples=samples,
            )
            row = {
                "case_id": case.id,
                "bucket": case.bucket,
                "rerun": result["rerun"],
                "output_sha": result["output_sha"],
                "judge_model": mdl.model,
                "judge_prompt_sha": shas["prompt_sha"],
                "judge_questions_sha": shas["questions_sha"],
                "pair_order": None,
                "swap_twin_verdict": None,
                **verdict,
            }
            records.append_jsonl(out_path, row)
            rows.append(row)
            if not quiet:
                print(
                    f"  judged {case.id} r{result['rerun']} {qid}: "
                    f"{verdict['verdict']} (p={verdict['p_pass']:.2f})"
                )
    return rows


def audit(judge_model: str = "local", samples: int = 5) -> dict:
    """Run the bias probes and report each with its n.

    The probes carry known-correct verdicts, so this measures the judge against
    something rather than against itself. Position runs the same pair in both
    orders; verbosity runs matched content at two lengths; self-preference needs
    a second model family and says so plainly when it does not have one.
    """
    path = os.path.join(JUDGE_DIR, "probes.yaml")
    probes = yaml.safe_load(open(path, encoding="utf-8")) or {}
    questions = load_questions()
    template = load_prompt_template()
    mdl = model_mod.build(judge_model)
    mdl.preflight()

    out: dict = {"judge_model": mdl.model, "samples_per_item": samples}

    verbosity = probes.get("verbosity", [])
    flips_to_padded = flips_to_plain = agree = 0
    for pair in verbosity:
        q = questions[pair["question_id"]]
        plain = judge_one(mdl, template, q, source=pair["source"],
                          question_input=pair["input"], answer=pair["plain"], samples=samples)
        padded = judge_one(mdl, template, q, source=pair["source"],
                           question_input=pair["input"], answer=pair["padded"], samples=samples)
        if plain["verdict"] == padded["verdict"]:
            agree += 1
        elif padded["verdict"] == "pass":
            flips_to_padded += 1
        else:
            flips_to_plain += 1
    from harness import stats

    out["verbosity"] = {
        "n_pairs": len(verbosity),
        "same_verdict": agree,
        "flipped_toward_padded": flips_to_padded,
        "flipped_toward_plain": flips_to_plain,
        "mcnemar_p": stats.mcnemar_exact(flips_to_plain, flips_to_padded).p,
        "note": "Content is held constant and only length is manipulated, so a "
                "difference here is length preference and not quality.",
    }

    position = probes.get("position", [])
    # A genuine pairwise probe: the same pair is judged in both orders with the
    # same question. Without position bias the verdict must FLIP when the better
    # answer changes slots. A verdict that stays put across the swap means the
    # judge picked a slot rather than an answer, so "inconsistent" here means the
    # two orders agreed, which is the opposite of how it reads at first glance
    # and is the whole reason the probe exists.
    flipped = stuck_on_slot1 = stuck_on_slot2 = 0
    for pair in position:
        q = questions[pair["question_id"]]
        ab = judge_one(mdl, template, q, source=pair["source"], question_input=pair["input"],
                       answer=f"ANSWER 1:\n{pair['a']}\n\nANSWER 2:\n{pair['b']}", samples=samples)
        ba = judge_one(mdl, template, q, source=pair["source"], question_input=pair["input"],
                       answer=f"ANSWER 1:\n{pair['b']}\n\nANSWER 2:\n{pair['a']}", samples=samples)
        if ab["verdict"] != ba["verdict"]:
            flipped += 1
        elif ab["verdict"] == "pass":
            stuck_on_slot1 += 1
        else:
            stuck_on_slot2 += 1
    n_pos = len(position)
    stuck = stuck_on_slot1 + stuck_on_slot2
    out["position"] = {
        "n_pairs": n_pos,
        "flipped_with_the_swap": flipped,
        "verdict_stuck_across_swap": stuck,
        "stuck_favoring_slot1": stuck_on_slot1,
        "stuck_favoring_slot2": stuck_on_slot2,
        "swap_consistency_rate": flipped / n_pos if n_pos else None,
        "swap_consistency_ci": str(stats.wilson(flipped, n_pos)) if n_pos else None,
        "directional_p": (
            stats.binom_tail_two_sided(min(stuck_on_slot1, stuck_on_slot2), stuck)
            if stuck else None
        ),
        "note": (
            "Without position bias the verdict flips when the better answer changes "
            "slots, so flipped/n is the consistency rate and a stuck verdict is a "
            "slot preference. The rate is the always-reportable number; the "
            "directional test detects only strong bias at these counts."
        ),
    }

    out["self_preference"] = {
        "runnable": False,
        "note": "Needs a second model family and human labels covering both. With one "
                "family loaded this is not a self-preference probe at all; it would be "
                "size asymmetry within a family, which is a different claim. Not run.",
    }
    return out
