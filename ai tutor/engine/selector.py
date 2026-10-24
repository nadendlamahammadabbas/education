"""Chooses what to ask next. Plans are lists of item tokens, deterministic per seed."""
from __future__ import annotations

import random

from .learner import ACTIVE, CANDIDATE, Status
from .registry import IDS
from .templates import BY_TARGET, make_token

SEED_SPACE = 10**9


def _tok(rng: random.Random, template, difficulty: int) -> str:
    return make_token(template.id, rng.randrange(SEED_SPACE), difficulty)


def diagnostic_plan(seed: int) -> list[str]:
    """10 items: each misconception probed twice, once per surface form, shuffled."""
    rng = random.Random(f"diag:{seed}")
    plan = [_tok(rng, t, 1) for m in IDS for t in BY_TARGET[m]]
    rng.shuffle(plan)
    return plan


def practice_plan(target: str, seed: int) -> list[str]:
    """4 items on the target (two surface forms, rising difficulty) + 1 interleaved other."""
    rng = random.Random(f"practice:{target}:{seed}")
    t0, t1 = BY_TARGET[target]
    other = rng.choice([m for m in IDS if m != target])
    ot = rng.choice(BY_TARGET[other])
    return [_tok(rng, t0, 1), _tok(rng, t0, 2), _tok(rng, ot, 1), _tok(rng, t1, 2), _tok(rng, t1, 3)]


def review_plan(seed: int) -> list[str]:
    """One mixed item per misconception, used when nothing is currently flagged."""
    rng = random.Random(f"review:{seed}")
    plan = [_tok(rng, rng.choice(BY_TARGET[m]), 2) for m in IDS]
    rng.shuffle(plan)
    return plan


def assessment_plan(seed: int, per: int = 5) -> list[str]:
    """Fixed-size assessment (pre/post) with `per` items per misconception."""
    rng = random.Random(f"test:{seed}")
    return [_tok(rng, BY_TARGET[m][i % 2], 1) for m in IDS for i in range(per)]


def choose_target(summary: dict[str, Status]) -> str | None:
    flagged = [(-s.p, m) for m, s in summary.items() if s.status in (ACTIVE, CANDIDATE)]
    return min(flagged)[1] if flagged else None
