"""Normalization, tokens and lexicon matching (docs/STATS.md §1.0)."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from importlib import resources

_LETTER_RUN = re.compile(r"([^\W\d_])\1+")
_TOKEN = re.compile(r"\w+(?:['’]\w+)*")
_URL = re.compile(r"https?://\S+|www\.\S+", re.I)
_EMAIL = re.compile(r"\S+@\S+\.\S+")
_PHONE = re.compile(r"\+?\d[\d\s\-]{7,}\d")

# Approximate emoji grapheme: base (+ variation selector, skin tone) joined by ZWJ, or a flag pair.
_BASE = (r"[☀-➿\U0001F300-\U0001FAFF⭐⭕⬅-⬇⤴⤵⬛⬜"
         r"〰〽㊗㊙‼⁉©®]")
EMOJI = re.compile(
    rf"[\U0001F1E6-\U0001F1FF]{{2}}|{_BASE}[️]?[\U0001F3FB-\U0001F3FF]?(?:‍{_BASE}[️]?[\U0001F3FB-\U0001F3FF]?)*"
)


def squash(s: str) -> str:
    """Case-fold and collapse runs of one letter ('sorryyy' -> 'sory'). For MATCHING only; never shown."""
    return _LETTER_RUN.sub(r"\1", s.lower().replace("’", "'"))


def tokens(text: str) -> list[str]:
    return _TOKEN.findall(_URL.sub(" ", text).lower())


def strip_urls(text: str) -> str:
    return _URL.sub(" ", text)


def has_url(text: str) -> bool:
    return bool(_URL.search(text))


def emojis(text: str) -> list[str]:
    return EMOJI.findall(text)


class Matcher:
    """Matches any phrase of a lexicon in already-squashed text."""

    def __init__(self, phrases: list[str]):
        parts = []
        for p in phrases:
            sq = squash(p)
            prefix = sq.endswith("*")
            sq = sq.rstrip("*")
            if not sq:
                continue
            esc = re.escape(sq)
            left = r"(?<!\w)" if re.match(r"\w", sq[0]) else ""
            right = "" if prefix or not re.match(r"\w", sq[-1]) else r"(?!\w)"
            parts.append(f"{left}{esc}{right}")
        self._rx = re.compile("|".join(sorted(parts, key=len, reverse=True)))

    def search(self, squashed: str) -> bool:
        return self._rx.search(squashed) is not None

    def count(self, squashed: str) -> int:
        return len(self._rx.findall(squashed))


@lru_cache(maxsize=1)
def _phrases() -> dict:
    raw = resources.files("lovelm").joinpath("lexicons/phrases.json").read_text(encoding="utf-8")
    return json.loads(raw)


@lru_cache(maxsize=None)
def matcher(name: str) -> Matcher:
    return Matcher(_phrases()[name])


def phrase_list(name: str) -> list[str]:
    return list(_phrases()[name])


@lru_cache(maxsize=1)
def stopwords() -> frozenset[str]:
    raw = resources.files("lovelm").joinpath("lexicons/stopwords.json").read_text(encoding="utf-8")
    return frozenset(json.loads(raw)["words"])


@lru_cache(maxsize=1)
def books() -> list[dict]:
    raw = resources.files("lovelm").joinpath("lexicons/books.json").read_text(encoding="utf-8")
    return json.loads(raw)["books"]
