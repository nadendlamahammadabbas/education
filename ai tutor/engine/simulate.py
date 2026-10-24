"""Simulated-learner harness. This is NOT evidence about real students: it checks that the
pipeline (diagnose -> target practice) behaves sensibly under stated assumptions.

Assumptions (also returned in the result):
  - A simulated learner holds 1-2 misconceptions; on an item targeting a held one it gives the
    bug answer with probability `strength` (starts 0.9). Otherwise it guesses a bug answer with
    probability GUESS, slips (wrong, not a bug) with probability SLIP, else answers correctly.
  - Every practice item on misconception m multiplies strength[m] by LEARN, in BOTH conditions.
    The only difference between conditions is how practice items are allocated."""
from __future__ import annotations

import random
from statistics import mean

from .classifier import MISCONCEPTION, classify, to_answer_str
from .learner import ACTIVE, CANDIDATE, summarize
from .registry import IDS
from .selector import choose_target, diagnostic_plan, practice_plan, review_plan, assessment_plan
from .templates import BY_TARGET, RANGE, item_from_token, make_token

START_STRENGTH, LEARN, GUESS, SLIP, PRACTICE_ITEMS = 0.9, 0.75, 0.03, 0.05, 15


def _respond(item, strengths, rng):
    r = rng.random()
    if r < max(strengths.get(item.target, 0.0), GUESS):
        return to_answer_str(item.bugs[item.target])
    if rng.random() < SLIP:
        return to_answer_str(item.correct + 7919)   # wrong, and never a bug answer
    return to_answer_str(item.correct)


def _ask(token, strengths, rng):
    item = item_from_token(token)
    d = classify(item, _respond(item, strengths, rng))
    return item, d.outcome


def _bug_rate(tokens, strengths, held, rng):
    hits = [_ask(t, strengths, rng)[1] == MISCONCEPTION
            for t in tokens if item_from_token(t).target in held]
    return mean(hits)


def _student(i, seed, condition):
    held = random.Random(f"held:{seed}:{i}").sample(IDS, random.Random(f"n:{seed}:{i}").choice([1, 2]))
    strengths = {m: START_STRENGTH for m in held}
    return set(held), strengths, random.Random(f"ans:{seed}:{i}:{condition}")


def _run_one(i, seed, condition):
    held, strengths, rng = _student(i, seed, condition)
    events, plan_rng = [], random.Random(f"plan:{seed}:{i}")
    for t in diagnostic_plan(i):
        item, outcome = _ask(t, strengths, rng)
        events.append((item.target, outcome))
    summary = summarize(events)
    flagged = {c: {m for m, s in summary.items() if s.status in levels} for c, levels in
               (("active", (ACTIVE,)), ("any", (ACTIVE, CANDIDATE)))}
    pre = _bug_rate(assessment_plan(10_000 + i), strengths, held, rng)

    done = 0
    while done < PRACTICE_ITEMS:
        if condition == "targeted":
            target = choose_target(summarize(events))
            plan = practice_plan(target, done + i) if target else review_plan(done + i)
        else:  # control: random allocation across all misconceptions
            plan = [make_token(plan_rng.choice(BY_TARGET[m]).id, plan_rng.randrange(10**9),
                               plan_rng.choice(list(RANGE))) for m in
                    (plan_rng.choice(IDS) for _ in range(5))]
        for t in plan[:PRACTICE_ITEMS - done]:
            item, outcome = _ask(t, strengths, rng)
            events.append((item.target, outcome))
            if item.target in strengths:
                strengths[item.target] *= LEARN
            done += 1
    post = _bug_rate(assessment_plan(20_000 + i), strengths, held, rng)
    return held, flagged, pre, post


def run(n: int = 200, seed: int = 7) -> dict:
    out = {"targeted": [], "control": []}
    tp = {"active": [0, 0, 0], "any": [0, 0, 0]}   # tp, fp, fn
    for i in range(n):
        for cond in out:
            held, flagged, pre, post = _run_one(i, seed, cond)
            out[cond].append((pre, post))
            if cond == "targeted":
                for lvl, found in flagged.items():
                    tp[lvl][0] += len(found & held)
                    tp[lvl][1] += len(found - held)
                    tp[lvl][2] += len(held - found)

    def pr(v):
        return {"precision": round(v[0] / max(v[0] + v[1], 1), 3), "recall": round(v[0] / max(v[0] + v[2], 1), 3)}

    return {
        "n": n, "seed": seed,
        "diagnosis": {"active_only": pr(tp["active"]), "candidate_or_active": pr(tp["any"])},
        "bug_rate": {c: {"pre": round(mean(p for p, _ in v), 3), "post": round(mean(q for _, q in v), 3)}
                     for c, v in out.items()},
        "assumptions": [
            f"{PRACTICE_ITEMS} practice items per learner in both conditions",
            f"each practice item multiplies the held misconception's strength by {LEARN}",
            f"start strength {START_STRENGTH}; guess-bug rate {GUESS}; slip rate {SLIP}",
            "simulated learners only; not evidence about real students",
        ],
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2))
