"""Golden cases + property checks (every template x 3 difficulties x 200 seeds),
with correct answers re-derived by sympy as an independent oracle."""
from fractions import Fraction

import sympy as sp

from engine.registry import IDS
from engine.templates import BY_TARGET, TEMPLATES, fr, generate, item_from_token

SEEDS = range(200)
X = sp.Symbol("x")


def _oracle(tid, p):
    if tid in ("m1_add", "m1_word"):
        return sp.Rational(p["a"], p["b"]) + sp.Rational(p["c"], p["d"])
    if tid in ("m2_add_mul", "m2_mul_add", "m3_sub_neg", "m3_neg_neg", "m4_square"):
        return sp.sympify(p["expr"])
    if tid == "m4_coef":
        return sp.Poly(sp.expand((X + p["a"]) ** 2), X).coeff_monomial(X)
    if tid in ("m5_same", "m5_diff"):
        r = sp.Rational
        return r(p["base"]) * (1 + r(p["p"], 100)) * (1 - r(p["q"], 100))
    raise AssertionError(tid)


def test_golden_cases():
    cases = {  # template id -> (params, correct, bug)
        "m1_add": ({"a": 1, "b": 2, "c": 1, "d": 3}, Fraction(5, 6), Fraction(2, 5)),
        "m2_add_mul": ({"a": 2, "b": 3, "c": 4}, 14, 20),
        "m3_sub_neg": ({"a": 5, "b": 3}, 8, 2),
        "m4_square": ({"k": 2, "a": 3}, 25, 13),
        "m4_coef": ({"a": 3}, 6, 0),
        "m5_same": ({"base": 100, "p": 20, "q": 20}, 96, 100),
    }
    for tid, (p, correct, bug) in cases.items():
        t = TEMPLATES[tid]
        assert t.correct(p) == correct and t.bug(p) == bug, tid


def test_every_misconception_has_two_templates():
    for m in IDS:
        assert len(BY_TARGET[m]) == 2, m


def test_properties_for_all_templates():
    for tid in TEMPLATES:
        for diff in (1, 2, 3):
            for seed in SEEDS:
                item = generate(tid, seed, diff)
                assert sp.Rational(item.correct.numerator, item.correct.denominator) == _oracle(tid, item.params), (tid, seed, diff)
                values = [item.correct, *item.bugs.values()]
                assert len(set(values)) == len(values), (tid, seed, diff)      # pairwise distinct
                assert generate(tid, seed, diff) == item                        # deterministic
                assert item_from_token(item.token) == item                      # token round-trip
                assert "None" not in item.prompt and "{" not in item.prompt


def test_feedback_text_is_well_formed():
    for tid, t in TEMPLATES.items():
        for seed in range(50):
            item = generate(tid, seed, 2)
            for text in (t.solution(item.params), t.bugnote(item.params)):
                assert text and "{" not in text and "None" not in text


def test_bad_inputs_rejected():
    for bad in (lambda: generate("nope", 1, 1), lambda: generate("m1_add", 1, 9), lambda: item_from_token("garbage")):
        try:
            bad()
        except (KeyError, ValueError):
            continue
        raise AssertionError("expected an error")


def test_fr_display():
    assert fr(Fraction(5, 1)) == "5" and fr(Fraction(5, 6)) == "5/6"
    assert fr(Fraction(125, 2)) == "62.5" and fr(Fraction(27, 20)) == "1.35"
