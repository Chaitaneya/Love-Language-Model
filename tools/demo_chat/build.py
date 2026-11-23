"""Orchestrates the whole build: structure -> text -> render, plus the truth sidecar."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from . import facts, structure, texts
from . import params as P
from .model import Slot
from .render import render
from .rng import Rng

_CINDY_ANY = re.compile(r"\b(cindy|cindyy|sindy|cindi)\b", re.I)
_CINDY_EXACT = re.compile(r"\bcindy\b", re.I)
_CUTE = re.compile(r"\bcute\b", re.I)


@dataclass
class Demo:
    slots: list[Slot]
    system: list
    text: str
    truth: dict


def build(seed: int = P.SEED) -> Demo:
    sched, sc, slots = structure.build_structure(seed)
    rng = Rng(seed)
    texts.realize(slots, rng.fork("texts"))
    texts.adjust_words(slots, rng.fork("words"))
    budgets = texts.assert_budgets(slots)
    text = render(slots, sc.system)
    return Demo(slots, sc.system, text, make_truth(slots, seed, budgets))


def make_truth(slots: list[Slot], seed: int, budgets: dict) -> dict:
    """Where every planted fact lives. Message ids are 0-based positions among non-system messages,
    which is exactly `lovelm` Message.id, so tests and the Exhibit A eval never hard-code line numbers."""
    ids: dict[str, list[int]] = {}
    for i, s in enumerate(slots):
        for tag in s.tags:
            if tag not in ("mod", "cry", "edited"):
                ids.setdefault(tag, []).append(i)
        if s.edited:
            ids.setdefault("edited", []).append(i)
        if s.role == "multiline":
            ids.setdefault("multiline", []).append(i)
        if s.kind == "text":
            if _CINDY_ANY.search(s.text):
                ids.setdefault("cindy_all", []).append(i)
            if _CINDY_EXACT.search(s.text):
                ids.setdefault("cindy_exact", []).append(i)
            if _CUTE.search(s.text):
                ids.setdefault("cute_literal_all", []).append(i)
        if s.kind == "deleted":
            ids.setdefault("deleted", []).append(i)
    measured = facts.summary(slots, P.R, P.T)
    measured["by_sender"] = {P.NAMES[k]: v for k, v in measured["by_sender"].items()}
    measured["reply_median_s"] = {P.NAMES[k]: v for k, v in measured["reply_median_s"].items()}
    measured["double_texts"] = {P.NAMES.get(k, k): v for k, v in measured["double_texts"].items()}
    queries = [
        {"q": "cindy", "mode": "keyword", "expect": ids["cindy_exact"]},
        {"q": "cindy", "mode": "fuzzy", "expect": ids["cindy_all"]},
        {"q": "sindy", "mode": "fuzzy", "expect": ids["cindy_all"]},
        {"q": "cute", "mode": "keyword", "expect": ids["cute_literal_all"]},
        {"q": "cute", "mode": "semantic", "expect": sorted(ids["cute_literal_all"] + ids["cute_paraphrase"])},
        {"q": "khana khaya", "mode": "fuzzy", "expect": ids["khana"]},
        {"q": "who said i love you first", "mode": "semantic", "expect": ids["first_ily"]},
    ]
    return {
        "schema": 1, "seed": seed, "format": "ios", "names": {"A": P.NAMES[P.R], "B": P.NAMES[P.T]},
        "message_count": len(slots), "ids": {k: sorted(v) for k, v in sorted(ids.items())},
        "budgets": budgets, "measured": measured, "queries": queries,
    }


def dumps_truth(truth: dict) -> str:
    return json.dumps(truth, indent=1, ensure_ascii=False, default=str) + "\n"
