from engine.simulate import run


def test_simulation_is_reproducible_and_sane():
    a, b = run(n=60, seed=3), run(n=60, seed=3)
    assert a == b
    for cond in ("targeted", "control"):
        assert a["bug_rate"][cond]["post"] < a["bug_rate"][cond]["pre"]
    assert a["bug_rate"]["targeted"]["post"] < a["bug_rate"]["control"]["post"]
    assert a["diagnosis"]["active_only"]["precision"] >= a["diagnosis"]["candidate_or_active"]["precision"]
    assert a["diagnosis"]["active_only"]["precision"] > 0.95
