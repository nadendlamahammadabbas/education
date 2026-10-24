"""End-to-end through the service + SQLite (no web framework needed)."""
from engine.classifier import to_answer_str
from engine.templates import item_from_token
from server.service import NotFound, Tutor
from server.store import Store


def _answer(tutor, lid, holds):
    """Answer the next question as a learner who holds `holds` misconceptions."""
    n = tutor.next_item(lid)
    item = item_from_token(tutor.store.queue_item(n["queue_id"])["token"])
    ans = item.bugs[item.target] if item.target in holds else item.correct
    return n, tutor.submit(lid, n["queue_id"], to_answer_str(ans))


def test_full_loop_diagnose_practice_recover():
    tutor = Tutor(Store(":memory:"))
    lid = tutor.start("Test")["learner_id"]
    for _ in range(10):
        n, r = _answer(tutor, lid, {"M1"})
        assert n["phase"] == "diagnostic"
    prof = tutor.profile(lid)
    status = {m["id"]: m["status"] for m in prof["misconceptions"]}
    assert status["M1"] == "active" and all(v == "none" for k, v in status.items() if k != "M1")

    n = tutor.next_item(lid)
    assert n["phase"] == "practice" and n["focus"] == "Adds numerators and denominators" and n["of"] == 5
    for _ in range(5):
        n, r = _answer(tutor, lid, set())          # learner has now fixed the misconception
        assert n["phase"] == "practice"
    assert {m["id"]: m["status"] for m in tutor.profile(lid)["misconceptions"]}["M1"] == "none"
    assert tutor.next_item(lid)["phase"] == "review"


def test_feedback_by_outcome():
    tutor = Tutor(Store(":memory:"))
    lid = tutor.start()["learner_id"]
    n = tutor.next_item(lid)
    item = item_from_token(tutor.store.queue_item(n["queue_id"])["token"])
    r = tutor.submit(lid, n["queue_id"], to_answer_str(item.bugs[item.target]))
    assert r["outcome"] == "misconception" and r["misconception"] and r["correct_answer"]
    n = tutor.next_item(lid)
    item = item_from_token(tutor.store.queue_item(n["queue_id"])["token"])
    r = tutor.submit(lid, n["queue_id"], to_answer_str(item.correct + 7919))
    assert r["outcome"] == "other_error" and r["message"].startswith("Not quite")
    n = tutor.next_item(lid)
    item = item_from_token(tutor.store.queue_item(n["queue_id"])["token"])
    assert tutor.submit(lid, n["queue_id"], to_answer_str(item.correct))["message"] == "Correct."


def test_invalid_input_is_not_recorded_and_question_stays_open():
    tutor = Tutor(Store(":memory:"))
    lid = tutor.start()["learner_id"]
    n = tutor.next_item(lid)
    for bad in ("", "abc", "1/0"):
        try:
            tutor.submit(lid, n["queue_id"], bad)
        except ValueError:
            continue
        raise AssertionError(bad)
    assert tutor.profile(lid)["answered"] == 0
    assert tutor.next_item(lid)["queue_id"] == n["queue_id"]


def test_guards():
    tutor = Tutor(Store(":memory:"))
    a, b = tutor.start()["learner_id"], tutor.start()["learner_id"]
    n = tutor.next_item(a)
    for call in (lambda: tutor.next_item(999), lambda: tutor.submit(b, n["queue_id"], "1"),
                 lambda: tutor.submit(a, 99999, "1")):
        try:
            call()
        except NotFound:
            continue
        raise AssertionError("expected NotFound")
    item = item_from_token(tutor.store.queue_item(n["queue_id"])["token"])
    tutor.submit(a, n["queue_id"], to_answer_str(item.correct))
    try:
        tutor.submit(a, n["queue_id"], to_answer_str(item.correct))
    except ValueError:
        pass
    else:
        raise AssertionError("double submit allowed")


def test_state_survives_reopening_the_database():
    import os, tempfile
    path = os.path.join(tempfile.mkdtemp(), "t.db")
    t1 = Tutor(Store(path))
    lid = t1.start("Persist")["learner_id"]
    _answer(t1, lid, {"M1", "M2", "M3", "M4", "M5"})
    t2 = Tutor(Store(path))
    assert t2.profile(lid)["answered"] == 1 and t2.next_item(lid)["step"] == 2


def test_learner_history():
    tutor = Tutor(Store(":memory:"))
    lid = tutor.start("HistoryTester")["learner_id"]
    _answer(tutor, lid, {"M1"})
    hist = tutor.history(lid)
    assert len(hist) == 1
    h = hist[0]
    assert h["phase"] == "diagnostic"
    assert "prompt" in h and "answer" in h and "outcome" in h and "correct_answer" in h
    assert "solution" in h and "target_name" in h


def test_manual_practice_trigger():
    tutor = Tutor(Store(":memory:"))
    lid = tutor.start("Deliberate")["learner_id"]
    res = tutor.practice(lid, "M3")
    assert res["target"] == "M3" and res["queued"] == 5
    n = tutor.next_item(lid)
    assert n["phase"] == "practice" and n["focus"] == "Sign error with negatives"
    assert n["step"] == 1 and n["of"] == 5
    # Invalid target rejected
    try:
        tutor.practice(lid, "M99")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for invalid target")


def test_list_and_reset_learner():
    tutor = Tutor(Store(":memory:"))
    lid1 = tutor.start("Alice")["learner_id"]
    lid2 = tutor.start("Bob")["learner_id"]
    learners = tutor.list_learners()
    assert len(learners) == 2
    assert {l["name"] for l in learners} == {"Alice", "Bob"}

    _answer(tutor, lid1, {"M1"})
    assert tutor.profile(lid1)["answered"] == 1
    tutor.reset(lid1)
    assert tutor.profile(lid1)["answered"] == 0
    n = tutor.next_item(lid1)
    assert n["phase"] == "diagnostic" and n["step"] == 1



