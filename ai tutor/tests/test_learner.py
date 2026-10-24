from engine.learner import ACTIVE, CANDIDATE, NONE, WINDOW, p_active, summarize

M, C, O = "misconception", "correct", "other_error"


def test_posterior_values():
    assert p_active(0, 0) == 0.5
    assert p_active(1, 0) == 0.75
    assert p_active(2, 0) == 0.875
    assert p_active(1, 1) == 0.5
    assert abs(p_active(2, 4) - 29 / 128) < 1e-12


def test_status_transitions():
    st = lambda ev: summarize(ev)["M1"].status
    assert st([]) == NONE
    assert st([("M1", M)]) == CANDIDATE
    assert st([("M1", M), ("M1", M)]) == ACTIVE
    assert st([("M1", M), ("M1", C)]) == NONE


def test_other_errors_and_other_targets_are_ignored():
    ev = [("M1", M), ("M1", O), ("M2", C), ("M2", C), ("M1", O)]
    assert summarize(ev)["M1"].status == CANDIDATE
    assert summarize(ev)["M1"].matches == 1 and summarize(ev)["M1"].corrects == 0


def test_recovery_after_practice():
    ev = [("M3", M), ("M3", M)] + [("M3", C)] * 4
    assert summarize(ev)["M3"].status == NONE


def test_window_forgets_old_evidence():
    ev = [("M4", M)] * 5 + [("M4", C)] * WINDOW
    s = summarize(ev)["M4"]
    assert s.matches == 0 and s.corrects == WINDOW


def test_misconceptions_are_independent():
    s = summarize([("M2", M), ("M2", M)])
    assert s["M2"].status == ACTIVE and all(s[m].status == NONE for m in ("M1", "M3", "M4", "M5"))
