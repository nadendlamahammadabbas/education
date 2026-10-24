"""Learner model. For each misconception we keep the last WINDOW informative
outcomes on items that target it ('misconception' = bug match, 'correct' = correct;
'other_error' carries no evidence). With a uniform Beta prior,
  a = 1 + matches, b = 1 + corrects,
  P(active) = P(Beta(a, b) > 0.5) = sum_{k<a} C(n, k) / 2^n,  n = a + b - 1
which is exact for integer a, b. The window lets a learner who has recovered
stop being flagged."""
from __future__ import annotations

from dataclasses import dataclass
from math import comb

from .classifier import CORRECT, MISCONCEPTION
from .registry import IDS

WINDOW = 6
ACTIVE_AT = 0.80      # needs two matches with no correct answers in the window
CANDIDATE_AT = 0.70   # one match with no correct answers
NONE, CANDIDATE, ACTIVE = "none", "candidate", "active"


@dataclass(frozen=True)
class Status:
    p: float
    status: str
    matches: int
    corrects: int


def p_active(matches: int, corrects: int) -> float:
    a, b = 1 + matches, 1 + corrects
    n = a + b - 1
    return sum(comb(n, k) for k in range(a)) / 2 ** n


def summarize(events: list[tuple[str, str]]) -> dict[str, Status]:
    """events: chronological (item_target, outcome). Returns status per misconception."""
    out = {}
    for m in IDS:
        informative = [o for t, o in events if t == m and o in (CORRECT, MISCONCEPTION)][-WINDOW:]
        matches = informative.count(MISCONCEPTION)
        corrects = informative.count(CORRECT)
        p = p_active(matches, corrects)
        status = ACTIVE if p >= ACTIVE_AT else CANDIDATE if p >= CANDIDATE_AT else NONE
        out[m] = Status(round(p, 4), status, matches, corrects)
    return out
