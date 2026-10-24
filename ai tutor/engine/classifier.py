"""Strict answer parsing and bug-matching classification. No guessing: an answer
either equals the correct value, equals a known bug's value, or is `other_error`."""
from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction

from .templates import Item

CORRECT = "correct"
MISCONCEPTION = "misconception"
OTHER = "other_error"

_NUMBER = re.compile(r"[+-]?[0-9]+(?:\.[0-9]+)?|[+-]?[0-9]+/[0-9]+")
BAD_INPUT = "Enter a whole number, a decimal like 0.75, or a fraction like 3/4."


def parse_answer(text: str) -> Fraction:
    s = (text or "").strip().replace("\u2212", "-")
    if not s or len(s) > 20 or not _NUMBER.fullmatch(s):
        raise ValueError(BAD_INPUT)
    try:
        return Fraction(s)
    except ZeroDivisionError:
        raise ValueError("The denominator cannot be zero.") from None


def to_answer_str(x: Fraction) -> str:
    return f"{x.numerator}/{x.denominator}"


@dataclass(frozen=True)
class Diagnosis:
    outcome: str                  # correct | misconception | other_error
    misconception: str | None     # set only when outcome == misconception
    answer: Fraction


def classify(item: Item, answer_text: str) -> Diagnosis:
    """Raises ValueError for unparseable input (callers must not record it)."""
    ans = parse_answer(answer_text)
    if ans == item.correct:
        return Diagnosis(CORRECT, None, ans)
    matches = [m for m, bug in item.bugs.items() if bug == ans]
    if len(matches) == 1:
        return Diagnosis(MISCONCEPTION, matches[0], ans)
    return Diagnosis(OTHER, None, ans)
