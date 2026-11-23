"""Stat registry, scoring helpers (docs/STATS.md §4.1) and the versus/couple builders."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from typing import Callable

from ..context import A, B, OTHER, Ctx


@dataclass
class Out:
    """What a stat function returns; the decorator adds the catalog fields around it."""

    score: float
    values: dict
    subject: str | None = None
    quote_ids: list[int] = field(default_factory=list)
    n: int | None = None  # sample size, for the confidence factor


@dataclass
class Stat:
    id: str
    pri: str
    kind: str  # couple | versus | event
    theme: str
    valence: str  # F flattering | N neutral | U unflattering (for the subject)
    spicy: bool
    countable: str  # "" | "always" | "spicy"  (may appear as a rating-box reason)
    charm: float  # editorial weight: breaks ties between equally extreme stats
    subject: str | None
    score: float
    values: dict
    quote_ids: list[int]
    lines: list[str] = field(default_factory=list)

    @property
    def rank(self) -> float:
        return round(self.score, 2) * self.charm  # scores equal to two decimals are ties, broken by editorial order

    def to_json(self) -> dict:
        return {
            "id": self.id, "pri": self.pri, "kind": self.kind, "theme": self.theme, "valence": self.valence,
            "spicy": self.spicy, "subject": self.subject, "score": round(self.score, 4),
            "values": self.values, "quote_ids": self.quote_ids, "lines": self.lines,
        }


@dataclass
class Spec:
    id: str
    pri: str
    kind: str
    theme: str
    valence: str
    spicy: bool
    countable: str
    charm: float
    n_min: int
    fn: Callable[[Ctx], Out | None]


REGISTRY: list[Spec] = []


def stat(id: str, pri: str, kind: str, theme: str, valence: str, *, spicy: bool = False,
         countable: str = "", charm: float = 1.0, n_min: int = 0):
    def deco(fn):
        REGISTRY.append(Spec(id, pri, kind, theme, valence, spicy, countable, charm, n_min, fn))
        return fn
    return deco


def run_all(c: Ctx) -> list[Stat]:
    out: list[Stat] = []
    for spec in REGISTRY:
        if spec.spicy and not c.spicy:
            continue
        r = spec.fn(c)
        if r is None:
            continue
        score = r.score
        if spec.n_min and r.n is not None:
            score *= 1 - math.exp(-r.n / (2 * spec.n_min))  # confidence
        out.append(Stat(spec.id, spec.pri, spec.kind, spec.theme, spec.valence, spec.spicy, spec.countable,
                        spec.charm, r.subject, max(0.0, min(1.0, score)), r.values, r.quote_ids))
    return out


# ---------------------------------------------------------------- scoring
def clip(x: float) -> float:
    return max(0.0, min(1.0, x))


def couple_score(v: float, wow: float) -> float:
    """Log scale between 'meh' (= wow / 20) and 'wow'."""
    if v <= 0:
        return 0.0
    return clip(math.log(v / (wow / 20)) / math.log(20))


def share_score(share: float, wow: float, base: float) -> float:
    """Linear excess of a share over its uniform baseline, reaching 1 at `wow`."""
    return clip((share - base) / (wow - base))


def versus(c: Ctx, a: float, b: float, *, r_wow: float = 5.0, lower_is_subject: bool = False,
           smooth: bool = True, extra: dict | None = None, n: int | None = None) -> Out | None:
    """Counts (smooth=True) or rates (smooth=False) for sides A and B. The 'winner' is the larger value;
    the subject is the winner unless `lower_is_subject`."""
    if a == b:
        return None
    hi, lo = max(a, b), min(a, b)
    r = (hi + 1) / (lo + 1) if smooth else (hi / lo if lo > 0 else r_wow * 2)
    win = A if a > b else B
    values = {"a": _num(a), "b": _num(b), "W": c.name(win), "L": c.name(OTHER[win]), "w": _num(hi),
              "l": _num(lo), "r": round(r, 3), "win": win}
    if extra:
        values.update(extra)
    return Out(clip(math.log(r) / math.log(r_wow)), values, OTHER[win] if lower_is_subject else win,
               n=n if n is not None else int(a + b) if smooth else None)


def _num(x: float):
    return int(x) if float(x).is_integer() else round(float(x), 3)


def iso(d: date) -> str:
    return d.isoformat()
