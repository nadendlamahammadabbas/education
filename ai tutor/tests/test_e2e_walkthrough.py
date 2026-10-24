"""Complete end-to-end user journey test covering:
- Diagnostic assessment (10 items)
- Automatic misconception identification (Beta posterior P(active) >= 0.80)
- Seamless transition to Targeted Practice (4 targeted + 1 interleaved item)
- Cognitive recovery through guided practice
- Transition to Mixed Review
- Attempt history inspection
- Deliberate practice trigger
- Profile reset
"""
from engine.classifier import to_answer_str
from engine.templates import item_from_token
from server.service import Tutor
from server.store import Store


def test_complete_student_journey():
    store = Store(":memory:")
    tutor = Tutor(store)

    lid = tutor.start("Arun")["learner_id"]

    # 1. Diagnostic phase: 10 items
    for step in range(1, 11):
        n = tutor.next_item(lid)
        assert n["phase"] == "diagnostic"
        assert n["step"] == step
        assert n["of"] == 10

        q = store.queue_item(n["queue_id"])
        item = item_from_token(q["token"])

        # Arun has misconception M1 ("Adds numerators and denominators")
        if item.target == "M1":
            ans = item.bugs["M1"]
        else:
            ans = item.correct

        res = tutor.submit(lid, n["queue_id"], to_answer_str(ans))
        if item.target == "M1":
            assert res["outcome"] == "misconception"
            assert res["misconception"] == "Adds numerators and denominators"
            assert "You added the tops and the bottoms" in res["message"]
        else:
            assert res["outcome"] == "correct"

    # Verify diagnostic summary
    prof = tutor.profile(lid)
    assert prof["answered"] == 10
    m_dict = {m["id"]: m for m in prof["misconceptions"]}
    assert m_dict["M1"]["status"] == "active"
    assert m_dict["M1"]["p"] >= 0.80
    assert all(m_dict[m]["status"] == "none" for m in ("M2", "M3", "M4", "M5"))

    # 2. Targeted Practice phase (5 items: 4 targeting M1 + 1 interleaved item)
    for step in range(1, 6):
        n = tutor.next_item(lid)
        assert n["phase"] == "practice"
        assert n["step"] == step
        assert n["of"] == 5

        q = store.queue_item(n["queue_id"])
        item = item_from_token(q["token"])

        # Arun has now learned and answers correctly!
        res = tutor.submit(lid, n["queue_id"], to_answer_str(item.correct))
        assert res["outcome"] == "correct"

    # Verify recovery: M1 is now mastered / none
    prof_after = tutor.profile(lid)
    assert prof_after["answered"] == 15
    m_dict_after = {m["id"]: m for m in prof_after["misconceptions"]}
    assert m_dict_after["M1"]["status"] == "none"
    assert m_dict_after["M1"]["p"] < 0.70

    # 3. Next phase is Mixed Review
    n_review = tutor.next_item(lid)
    assert n_review["phase"] == "review"

    # 4. History log contains all 15 attempts with solutions and correct answers
    hist = tutor.history(lid)
    assert len(hist) == 15
    for h in hist:
        assert h["prompt"] and h["answer"] and h["outcome"] and h["solution"]

    # 5. Deliberate practice trigger
    prac = tutor.practice(lid, "M4")
    assert prac["target"] == "M4" and prac["queued"] == 5
    n_prac = tutor.next_item(lid)
    assert n_prac["phase"] == "practice" and n_prac["focus"] == "Squares a sum term by term"

    # 6. Reset learner
    tutor.reset(lid)
    assert tutor.profile(lid)["answered"] == 0
    assert tutor.next_item(lid)["phase"] == "diagnostic"

