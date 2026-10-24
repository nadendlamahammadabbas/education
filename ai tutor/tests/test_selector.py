from collections import Counter

from engine.learner import summarize
from engine.registry import IDS
from engine.selector import choose_target, diagnostic_plan, practice_plan, review_plan, assessment_plan
from engine.templates import item_from_token, token_target


def test_diagnostic_covers_each_misconception_twice_with_both_forms():
    plan = diagnostic_plan(42)
    assert len(plan) == 10 and len(set(plan)) == 10
    assert Counter(token_target(t) for t in plan) == {m: 2 for m in IDS}
    assert len({t.split(":")[0] for t in plan}) == 10     # all 10 templates used once
    assert plan == diagnostic_plan(42) and plan != diagnostic_plan(43)


def test_practice_plan_composition():
    for target in IDS:
        plan = practice_plan(target, 5)
        targets = [token_target(t) for t in plan]
        assert len(plan) == 5 and targets.count(target) == 4
        assert [t.split(":")[0] for t in plan if token_target(t) == target].count(plan[0].split(":")[0]) == 2
        assert plan == practice_plan(target, 5)
        for t in plan:
            item_from_token(t)


def test_review_and_test_plans():
    assert sorted(token_target(t) for t in review_plan(1)) == sorted(IDS)
    tp = assessment_plan(1, per=5)
    assert len(tp) == 25 and Counter(token_target(t) for t in tp) == {m: 5 for m in IDS}


def test_choose_target():
    assert choose_target(summarize([])) is None
    ev = [("M2", "misconception")] + [("M5", "misconception")] * 2
    assert choose_target(summarize(ev)) == "M5"        # highest posterior wins
    assert choose_target(summarize([("M3", "misconception")])) == "M3"
