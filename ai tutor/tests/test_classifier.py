from fractions import Fraction

from engine.classifier import CORRECT, MISCONCEPTION, OTHER, classify, parse_answer, to_answer_str
from engine.templates import TEMPLATES, generate


def _rejects(text):
    try:
        parse_answer(text)
    except ValueError:
        return True
    return False


def test_parser_accepts():
    assert parse_answer(" 3/4 ") == Fraction(3, 4)
    assert parse_answer("0.75") == Fraction(3, 4)
    assert parse_answer("-2") == -2 and parse_answer("+5") == 5
    assert parse_answer("\u22122") == -2          # unicode minus
    assert parse_answer("10/4") == Fraction(5, 2)  # unsimplified is fine


def test_parser_rejects():
    for bad in ("", "   ", "abc", "1/0", "1.5/2", "1 1/2", "1e3", "\u0663", "--2", "2/", "/2", "1" * 30, None):
        assert _rejects(bad), repr(bad)


def test_golden_diagnoses():
    it = generate("m1_add", 3, 1)
    p = it.params
    assert classify(it, f"{p['a'] + p['c']}/{p['b'] + p['d']}").misconception == "M1"


def test_every_bug_is_detected_and_nothing_else_is_forced():
    for tid, t in TEMPLATES.items():
        for seed in range(150):
            it = generate(tid, seed, 1 + seed % 3)
            assert classify(it, to_answer_str(it.correct)).outcome == CORRECT
            d = classify(it, to_answer_str(it.bugs[t.target]))
            assert (d.outcome, d.misconception) == (MISCONCEPTION, t.target), (tid, seed)
            other = classify(it, to_answer_str(it.correct + 7919))
            assert (other.outcome, other.misconception) == (OTHER, None)


def test_equivalent_forms_count_as_correct():
    it = generate("m5_same", 1, 1)
    assert classify(it, f"{float(it.correct)}").outcome == CORRECT  # exact binary decimals only
