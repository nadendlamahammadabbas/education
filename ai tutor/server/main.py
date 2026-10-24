"""Thin FastAPI wrapper. Run:  uvicorn server.main:create_app --factory --reload"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from engine.simulate import run as run_simulation

from .service import NotFound, Tutor
from .store import Store

INDEX = Path(__file__).resolve().parent.parent / "web" / "index.html"


class StartIn(BaseModel):
    name: str = Field(default="Learner", max_length=40)


class AnswerIn(BaseModel):
    queue_id: int
    answer: str = Field(max_length=40)


class PracticeIn(BaseModel):
    target: str = Field(max_length=10)



@lru_cache(maxsize=8)
def _cached_evidence(n: int) -> dict:
    return run_simulation(n=n)



def create_app(db_path: str | None = None) -> FastAPI:
    tutor = Tutor(Store(db_path or os.environ.get("TUTOR_DB", "tutor.db")))
    app = FastAPI(title="Misconception Tutor")

    @app.get("/")
    def index():
        return FileResponse(INDEX)

    @app.get("/api/learners")
    def list_learners():
        return tutor.list_learners()

    @app.post("/api/learners")
    def start(body: StartIn):
        return tutor.start(body.name)

    @app.post("/api/learners/{learner_id}/reset")
    def reset(learner_id: int):
        try:
            return tutor.reset(learner_id)
        except NotFound as e:
            raise HTTPException(404, str(e)) from None


    @app.get("/api/learners/{learner_id}/next")
    def next_item(learner_id: int):
        try:
            return tutor.next_item(learner_id)
        except NotFound as e:
            raise HTTPException(404, str(e)) from None

    @app.post("/api/learners/{learner_id}/answer")
    def answer(learner_id: int, body: AnswerIn):
        try:
            return tutor.submit(learner_id, body.queue_id, body.answer)
        except NotFound as e:
            raise HTTPException(404, str(e)) from None
        except ValueError as e:
            raise HTTPException(400, str(e)) from None

    @app.get("/api/learners/{learner_id}/profile")
    def profile(learner_id: int):
        try:
            return tutor.profile(learner_id)
        except NotFound as e:
            raise HTTPException(404, str(e)) from None

    @app.get("/api/learners/{learner_id}/history")
    def history(learner_id: int):
        try:
            return tutor.history(learner_id)
        except NotFound as e:
            raise HTTPException(404, str(e)) from None

    @app.post("/api/learners/{learner_id}/practice")
    def practice(learner_id: int, body: PracticeIn):
        try:
            return tutor.practice(learner_id, body.target)
        except NotFound as e:
            raise HTTPException(404, str(e)) from None
        except ValueError as e:
            raise HTTPException(400, str(e)) from None

    @app.get("/api/evidence")
    def evidence(n: int = 150):
        if not (10 <= n <= 300):
            raise HTTPException(400, "Cohort size n must be between 10 and 300.")
        return _cached_evidence(n)


    return app
