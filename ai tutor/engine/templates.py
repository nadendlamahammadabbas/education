"""Seeded problem templates. Every template computes:
  - correct(params): the right answer (exact Fraction arithmetic, no floats)
  - bug(params):     the answer a student holding the target misconception gives
An item is only emitted when correct != bug, so a bug match is unambiguous.
The same (template_id, seed, difficulty) always yields the same item."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Callable

RANGE = {1: 6, 2: 9, 3: 12}   # upper bound for small integers, by difficulty
MAX_TRIES = 200
PCTS = (10, 20, 25, 50)
BASES = (100, 200, 250, 400, 500, 800)


def fr(x: Fraction) -> str:
    """Display form: integer, exact terminating decimal, else n/d."""
    x = Fraction(x)
    if x.denominator == 1:
        return str(x.numerator)
    d = x.denominator
    while d % 2 == 0:
        d //= 2
    while d % 5 == 0:
        d //= 5
    if d == 1:
        return format(Decimal(x.numerator) / Decimal(x.denominator), "f")
    return f"{x.numerator}/{x.denominator}"


@dataclass(frozen=True)
class Template:
    id: str
    target: str
    hint: str
    params: Callable[[random.Random, int], dict]
    prompt: Callable[[dict], str]
    correct: Callable[[dict], Fraction]
    bug: Callable[[dict], Fraction]
    solution: Callable[[dict], str]
    bugnote: Callable[[dict], str]


@dataclass(frozen=True)
class Item:
    template_id: str
    seed: int
    difficulty: int
    target: str
    prompt: str
    hint: str
    params: dict
    correct: Fraction
    bugs: dict  # misconception id -> Fraction

    @property
    def token(self) -> str:
        return make_token(self.template_id, self.seed, self.difficulty)


def make_token(template_id: str, seed: int, difficulty: int) -> str:
    return f"{template_id}:{seed}:{difficulty}"


FRACTION_HINT = "Enter a fraction like 5/6, or an exact decimal."
NUMBER_HINT = "Enter a number. Use - for negatives."

# ---- M1: fractions -------------------------------------------------------

def _m1_params(rng, diff):
    b, d = rng.sample(range(2, RANGE[diff] + 1), 2)
    return {"a": rng.randint(1, b - 1), "b": b, "c": rng.randint(1, d - 1), "d": d}


def _m1_correct(p):
    return Fraction(p["a"], p["b"]) + Fraction(p["c"], p["d"])


def _m1_bug(p):
    return Fraction(p["a"] + p["c"], p["b"] + p["d"])


def _m1_solution(p):
    a, b, c, d = p["a"], p["b"], p["c"], p["d"]
    L = math.lcm(b, d)
    x, y = a * L // b, c * L // d
    return f"Use a common denominator of {L}: {x}/{L} + {y}/{L} = {x + y}/{L} = {_m1_correct(p)}."


def _m1_bugnote(p):
    a, b, c, d = p["a"], p["b"], p["c"], p["d"]
    return (f"You added the tops and the bottoms: ({a}+{c})/({b}+{d}) = {_m1_bug(p)}. "
            "The bottom number names the size of the pieces, so it can't be added.")


# ---- M2: order of operations --------------------------------------------

def _m2a_params(rng, diff):
    hi = RANGE[diff]
    a, b, c = (rng.randint(2, hi) for _ in range(3))
    return {"a": a, "b": b, "c": c, "expr": f"{a}+{b}*{c}"}


def _m2b_params(rng, diff):
    hi = RANGE[diff]
    a, b, c, d = (rng.randint(2, hi) for _ in range(4))
    return {"a": a, "b": b, "c": c, "d": d, "expr": f"{a}*{b}+{c}*{d}"}


# ---- M3: negatives -------------------------------------------------------

def _ab_params(rng, diff):
    hi = RANGE[diff] + 3
    return {"a": rng.randint(1, hi), "b": rng.randint(1, hi)}


def _m3a_params(rng, diff):
    p = _ab_params(rng, diff)
    p["expr"] = f"{p['a']}-(-{p['b']})"
    return p


def _m3b_params(rng, diff):
    p = _ab_params(rng, diff)
    p["expr"] = f"-{p['a']}-(-{p['b']})"
    return p


# ---- M4: squaring a sum --------------------------------------------------

def _m4a_params(rng, diff):
    hi = RANGE[diff]
    k, a = rng.randint(2, hi), rng.randint(2, hi)
    return {"k": k, "a": a, "expr": f"({k}+{a})**2"}


def _m4b_params(rng, diff):
    return {"a": rng.randint(2, RANGE[diff])}


# ---- M5: percentages -----------------------------------------------------

def _m5a_params(rng, diff):
    p = rng.choice(PCTS)
    return {"base": rng.choice(BASES), "p": p, "q": p}


def _m5b_params(rng, diff):
    p, q = rng.sample(PCTS, 2)
    return {"base": rng.choice(BASES), "p": p, "q": q}


def _m5_correct(p):
    return Fraction(p["base"] * (100 + p["p"]) * (100 - p["q"]), 10000)


def _m5_bug(p):
    return Fraction(p["base"] * (100 + p["p"] - p["q"]), 100)


def _m5_solution(p):
    up = Fraction(p["base"] * (100 + p["p"]), 100)
    return (f"After +{p['p']}% the value is {fr(up)}. The -{p['q']}% is then taken of {fr(up)}, "
            f"not of {p['base']}, so the final value is {fr(_m5_correct(p))}.")


def _m5_bugnote(p):
    return (f"You combined +{p['p']}% and -{p['q']}% as {p['p'] - p['q']}%, giving {fr(_m5_bug(p))}. "
            "The second change applies to the new amount, so the changes don't simply cancel.")


_LEFT_TO_RIGHT = "You worked left to right, but multiplication is done before addition."

TEMPLATES: dict[str, Template] = {t.id: t for t in (
    Template("m1_add", "M1", FRACTION_HINT, _m1_params,
             lambda p: f"Work out {p['a']}/{p['b']} + {p['c']}/{p['d']}.",
             _m1_correct, _m1_bug, _m1_solution, _m1_bugnote),
    Template("m1_word", "M1", FRACTION_HINT, _m1_params,
             lambda p: (f"Priya eats {p['a']}/{p['b']} of a pizza, then {p['c']}/{p['d']} of "
                        "another pizza of the same size. How much pizza has she eaten in total?"),
             _m1_correct, _m1_bug, _m1_solution, _m1_bugnote),
    Template("m2_add_mul", "M2", NUMBER_HINT, _m2a_params,
             lambda p: f"Evaluate {p['a']} + {p['b']} × {p['c']}.",
             lambda p: Fraction(p["a"] + p["b"] * p["c"]),
             lambda p: Fraction((p["a"] + p["b"]) * p["c"]),
             lambda p: f"Multiply first: {p['b']} × {p['c']} = {p['b'] * p['c']}, then {p['a']} + {p['b'] * p['c']} = {p['a'] + p['b'] * p['c']}.",
             lambda p: f"{_LEFT_TO_RIGHT} ({p['a']} + {p['b']}) × {p['c']} = {(p['a'] + p['b']) * p['c']}."),
    Template("m2_mul_add", "M2", NUMBER_HINT, _m2b_params,
             lambda p: f"Evaluate {p['a']} × {p['b']} + {p['c']} × {p['d']}.",
             lambda p: Fraction(p["a"] * p["b"] + p["c"] * p["d"]),
             lambda p: Fraction((p["a"] * p["b"] + p["c"]) * p["d"]),
             lambda p: f"Do both multiplications first: {p['a'] * p['b']} + {p['c'] * p['d']} = {p['a'] * p['b'] + p['c'] * p['d']}.",
             lambda p: f"{_LEFT_TO_RIGHT} (({p['a']} × {p['b']}) + {p['c']}) × {p['d']} = {(p['a'] * p['b'] + p['c']) * p['d']}."),
    Template("m3_sub_neg", "M3", NUMBER_HINT, _m3a_params,
             lambda p: f"Evaluate {p['a']} − (−{p['b']}).",
             lambda p: Fraction(p["a"] + p["b"]),
             lambda p: Fraction(p["a"] - p["b"]),
             lambda p: f"Subtracting a negative is adding: {p['a']} − (−{p['b']}) = {p['a']} + {p['b']} = {p['a'] + p['b']}.",
             lambda p: f"You treated − (−{p['b']}) as − {p['b']}, giving {p['a'] - p['b']}."),
    Template("m3_neg_neg", "M3", NUMBER_HINT, _m3b_params,
             lambda p: f"Evaluate −{p['a']} − (−{p['b']}).",
             lambda p: Fraction(p["b"] - p["a"]),
             lambda p: Fraction(-p["a"] - p["b"]),
             lambda p: f"−{p['a']} − (−{p['b']}) = −{p['a']} + {p['b']} = {p['b'] - p['a']}.",
             lambda p: f"You treated − (−{p['b']}) as − {p['b']}, giving −{p['a']} − {p['b']} = {-p['a'] - p['b']}."),
    Template("m4_square", "M4", NUMBER_HINT, _m4a_params,
             lambda p: f"Evaluate (x + {p['a']})² when x = {p['k']}.",
             lambda p: Fraction((p["k"] + p["a"]) ** 2),
             lambda p: Fraction(p["k"] ** 2 + p["a"] ** 2),
             lambda p: f"Add inside the brackets first: ({p['k']} + {p['a']})² = {p['k'] + p['a']}² = {(p['k'] + p['a']) ** 2}.",
             lambda p: (f"You squared each term separately: {p['k']}² + {p['a']}² = {p['k'] ** 2 + p['a'] ** 2}. "
                        f"But (x + {p['a']})² means (x + {p['a']})(x + {p['a']}), which has a middle term.")),
    Template("m4_coef", "M4", NUMBER_HINT, _m4b_params,
             lambda p: f"In the expansion of (x + {p['a']})², what is the coefficient of x?",
             lambda p: Fraction(2 * p["a"]),
             lambda p: Fraction(0),
             lambda p: f"(x + {p['a']})(x + {p['a']}) = x² + {p['a']}x + {p['a']}x + {p['a'] ** 2}, so the coefficient of x is {2 * p['a']}.",
             lambda p: f"You expanded it as x² + {p['a'] ** 2}, which drops the middle term."),
    Template("m5_same", "M5", NUMBER_HINT, _m5a_params,
             lambda p: f"A price of {p['base']} goes up by {p['p']}% and then down by {p['q']}%. What is the final price?",
             _m5_correct, _m5_bug, _m5_solution, _m5_bugnote),
    Template("m5_diff", "M5", NUMBER_HINT, _m5b_params,
             lambda p: f"A share worth {p['base']} rises {p['p']}% on Monday, then falls {p['q']}% on Tuesday. What is it worth after Tuesday?",
             _m5_correct, _m5_bug, _m5_solution, _m5_bugnote),
)}

BY_TARGET: dict[str, tuple[Template, ...]] = {}
for _t in TEMPLATES.values():
    BY_TARGET[_t.target] = BY_TARGET.get(_t.target, ()) + (_t,)


def generate(template_id: str, seed: int, difficulty: int = 1) -> Item:
    if template_id not in TEMPLATES:
        raise KeyError(f"unknown template {template_id!r}")
    if difficulty not in RANGE:
        raise ValueError(f"difficulty must be one of {sorted(RANGE)}")
    t = TEMPLATES[template_id]
    rng = random.Random(f"{template_id}:{seed}:{difficulty}")
    for _ in range(MAX_TRIES):
        params = t.params(rng, difficulty)
        correct, bug = t.correct(params), t.bug(params)
        if correct != bug:
            return Item(template_id, seed, difficulty, t.target, t.prompt(params), t.hint,
                        params, correct, {t.target: bug})
    raise RuntimeError(f"could not generate a distinguishable item for {template_id}")


def item_from_token(token: str) -> Item:
    try:
        tid, seed, diff = token.split(":")
        return generate(tid, int(seed), int(diff))
    except (ValueError, KeyError) as e:
        raise ValueError(f"bad item token {token!r}") from e


def token_target(token: str) -> str:
    return TEMPLATES[token.split(":")[0]].target
