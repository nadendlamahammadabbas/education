"""HTTP layer. Skipped automatically if FastAPI/httpx are not installed."""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from engine.classifier import to_answer_str  # noqa: E402
from engine.templates import item_from_token  # noqa: E402
from server.main import create_app  # noqa: E402


def test_http_flow():
    app = create_app(":memory:")
    c = TestClient(app)
    assert c.get("/").status_code == 200
    lid = c.post("/api/learners", json={"name": "Ada"}).json()["learner_id"]
    n = c.get(f"/api/learners/{lid}/next").json()
    assert n["step"] == 1 and n["of"] == 10 and "answer" not in n and "correct" not in n
    assert c.post(f"/api/learners/{lid}/answer", json={"queue_id": n["queue_id"], "answer": "abc"}).status_code == 400
    assert c.get("/api/learners/9999/next").status_code == 404
    r = c.post(f"/api/learners/{lid}/answer", json={"queue_id": n["queue_id"], "answer": "0"})
    assert r.status_code == 200 and r.json()["outcome"] in {"correct", "misconception", "other_error"}
    assert len(c.get(f"/api/learners/{lid}/profile").json()["misconceptions"]) == 5
    assert c.post(f"/api/learners/{lid}/answer", json={"queue_id": n["queue_id"], "answer": "0"}).status_code == 400
    assert c.post(f"/api/learners/{lid}/answer", json={"queue_id": n["queue_id"], "answer": "x" * 99}).status_code == 422


def test_evidence_endpoint():
    c = TestClient(create_app(":memory:"))
    ev = c.get("/api/evidence").json()
    assert ev["bug_rate"]["targeted"]["post"] < ev["bug_rate"]["control"]["post"]
    ev50 = c.get("/api/evidence?n=50").json()
    assert ev50["n"] == 50
    assert c.get("/api/evidence?n=5").status_code == 400
    assert c.get("/api/evidence?n=5000").status_code == 400



def test_history_endpoint():
    app = create_app(":memory:")
    c = TestClient(app)
    lid = c.post("/api/learners", json={"name": "Ada"}).json()["learner_id"]
    n = c.get(f"/api/learners/{lid}/next").json()
    c.post(f"/api/learners/{lid}/answer", json={"queue_id": n["queue_id"], "answer": "0"})
    h = c.get(f"/api/learners/{lid}/history").json()
    assert len(h) == 1
    assert "prompt" in h[0] and "solution" in h[0]


def test_practice_endpoint():
    app = create_app(":memory:")
    c = TestClient(app)
    lid = c.post("/api/learners", json={"name": "Ada"}).json()["learner_id"]
    r = c.post(f"/api/learners/{lid}/practice", json={"target": "M2"})
    assert r.status_code == 200 and r.json()["target"] == "M2"
    n = c.get(f"/api/learners/{lid}/next").json()
    assert n["phase"] == "practice" and n["focus"] == "Ignores order of operations"
    assert c.post(f"/api/learners/{lid}/practice", json={"target": "UNKNOWN"}).status_code == 400


def test_learners_list_and_reset_endpoints():
    app = create_app(":memory:")
    c = TestClient(app)
    lid = c.post("/api/learners", json={"name": "Charlie"}).json()["learner_id"]
    learners = c.get("/api/learners").json()
    assert any(l["id"] == lid for l in learners)
    n = c.get(f"/api/learners/{lid}/next").json()
    c.post(f"/api/learners/{lid}/answer", json={"queue_id": n["queue_id"], "answer": "0"})
    assert c.post(f"/api/learners/{lid}/reset").status_code == 200
    assert c.get(f"/api/learners/{lid}/profile").json()["answered"] == 0



