"""Application logic, independent of the web framework (so it is unit-testable)."""
from __future__ import annotations

import secrets

from engine.classifier import CORRECT, MISCONCEPTION, classify
from engine.learner import summarize
from engine.registry import IDS, MISCONCEPTIONS
from engine.selector import choose_target, diagnostic_plan, practice_plan, review_plan
from engine.templates import TEMPLATES, fr, item_from_token, token_target

from .store import Store

HISTORY = 12


class NotFound(KeyError):
    pass


class Tutor:
    def __init__(self, store: Store):
        self.store = store

    # -- lifecycle ---------------------------------------------------------
    def start(self, name: str = "Learner") -> dict:
        seed = secrets.randbelow(10**9)
        lid = self.store.create_learner((name or "Learner").strip()[:40] or "Learner", seed)
        self.store.add_queue(lid, "diagnostic", [(t, token_target(t)) for t in diagnostic_plan(seed)])
        return {"learner_id": lid}

    def _learner(self, learner_id: int):
        row = self.store.learner(learner_id)
        if row is None:
            raise NotFound("learner not found")
        return row

    def _enqueue_followup(self, learner) -> None:
        events = self.store.events(learner["id"])
        target = choose_target(summarize(events))
        seed = learner["seed"] + len(events)
        if target:
            plan, phase = practice_plan(target, seed), "practice"
        else:
            plan, phase = review_plan(seed), "review"
        self.store.add_queue(learner["id"], phase, [(t, token_target(t)) for t in plan])

    def practice(self, learner_id: int, target: str) -> dict:
        learner = self._learner(learner_id)
        if target not in IDS:
            raise ValueError(f"Unknown misconception target: {target}")
        self.store.clear_undone(learner_id)
        seed = learner["seed"] + len(self.store.events(learner_id))
        plan = practice_plan(target, seed)
        self.store.add_queue(learner_id, "practice", [(t, token_target(t)) for t in plan])
        return {"queued": len(plan), "target": target, "focus": MISCONCEPTIONS[target].name}


    # -- asking ------------------------------------------------------------
    def next_item(self, learner_id: int) -> dict:
        learner = self._learner(learner_id)
        q = self.store.first_undone(learner_id)
        if q is None:
            self._enqueue_followup(learner)
            q = self.store.first_undone(learner_id)
        item = item_from_token(q["token"])
        done, total = self.store.batch_progress(learner_id, q["batch"])
        return {
            "queue_id": q["id"], "phase": q["phase"], "prompt": item.prompt, "hint": item.hint,
            "step": done + 1, "of": total,
            "focus": MISCONCEPTIONS[q["target"]].name if q["phase"] == "practice" else None,
        }

    def submit(self, learner_id: int, queue_id: int, answer: str) -> dict:
        self._learner(learner_id)
        q = self.store.queue_item(queue_id)
        if q is None or q["learner_id"] != learner_id:
            raise NotFound("question not found")
        if q["done"]:
            raise ValueError("This question was already answered.")
        item = item_from_token(q["token"])
        diag = classify(item, answer)           # ValueError on bad input -> nothing recorded
        self.store.record_attempt(learner_id, q, answer.strip(), diag.outcome)
        tpl = TEMPLATES[item.template_id]
        if diag.outcome == CORRECT:
            message = "Correct."
        elif diag.outcome == MISCONCEPTION:
            message = f"{tpl.bugnote(item.params)} {tpl.solution(item.params)}"
        else:
            message = f"Not quite. {tpl.solution(item.params)}"
        return {
            "outcome": diag.outcome,
            "misconception": MISCONCEPTIONS[diag.misconception].name if diag.misconception else None,
            "correct_answer": fr(item.correct),
            "message": message,
            "profile": self.profile(learner_id),
        }

    # -- reporting ---------------------------------------------------------
    def profile(self, learner_id: int) -> dict:
        learner = self._learner(learner_id)
        events = self.store.events(learner_id)
        summary = summarize(events)
        rows = []
        for m in IDS:
            hist = [o for t, o in events if t == m][-HISTORY:]
            s = summary[m]
            rows.append({"id": m, "name": MISCONCEPTIONS[m].name, "description": MISCONCEPTIONS[m].description,
                         "p": s.p, "status": s.status, "history": hist})
        return {"learner": {"id": learner_id, "name": learner["name"]}, "answered": len(events),
                "misconceptions": rows}

    def history(self, learner_id: int) -> list[dict]:
        self._learner(learner_id)
        rows = self.store.attempts(learner_id)
        records = []
        for r in rows:
            item = item_from_token(r["token"])
            tpl = TEMPLATES[item.template_id]
            records.append({
                "id": r["id"],
                "queue_id": r["queue_id"],
                "token": r["token"],
                "phase": r["phase"],
                "target": r["target"],
                "target_name": MISCONCEPTIONS[r["target"]].name,
                "prompt": item.prompt,
                "answer": r["answer"],
                "outcome": r["outcome"],
                "correct_answer": fr(item.correct),
                "solution": tpl.solution(item.params),
                "ts": r["ts"],
            })
        return records

    def list_learners(self) -> list[dict]:
        rows = self.store.list_learners()
        return [{"id": r["id"], "name": r["name"], "created": r["created"], "answered": r["answered"]} for r in rows]

    def reset(self, learner_id: int) -> dict:
        learner = self._learner(learner_id)
        self.store.reset_learner(learner_id)
        self.store.add_queue(learner_id, "diagnostic", [(t, token_target(t)) for t in diagnostic_plan(learner["seed"])])
        return {"status": "reset", "learner_id": learner_id}


