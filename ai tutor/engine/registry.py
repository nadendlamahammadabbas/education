"""The misconception taxonomy. Each id is attached to templates (templates.py)
that can reveal it through one specific, predictable wrong answer."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Misconception:
    id: str
    name: str
    description: str


MISCONCEPTIONS: dict[str, Misconception] = {
    m.id: m
    for m in (
        Misconception("M1", "Adds numerators and denominators",
                      "Treats a/b + c/d as (a+c)/(b+d) instead of using a common denominator."),
        Misconception("M2", "Ignores order of operations",
                      "Evaluates an expression strictly left to right instead of multiplying first."),
        Misconception("M3", "Sign error with negatives",
                      "Treats subtracting a negative number as subtracting a positive one."),
        Misconception("M4", "Squares a sum term by term",
                      "Treats (x + a)^2 as x^2 + a^2, dropping the middle term."),
        Misconception("M5", "Percent changes cancel out",
                      "Combines successive percentage changes additively, ignoring the changing base."),
    )
}
IDS: tuple[str, ...] = tuple(MISCONCEPTIONS)
