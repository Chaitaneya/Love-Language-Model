"""The shared analysis context: conversations, turns, replies, days, streaks, silences. Computed once
from a parsed Chat using exactly the definitions of docs/STATS.md §1.0. Sides are 'A' (first person
to appear) and 'B'; display names live in `names`."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from . import config
from .model import Chat, Message
from .rng import Rng
from .text import matcher, squash, tokens

A, B = "A", "B"
OTHER = {A: B, B: A}
_WORD = re.compile(r"[^\W\d_][\w']*")
_DIGITS = re.compile(r"\d{4,}")
_PHONE = re.compile(r"\+?\d[\d\s\-]{7,}\d")
_EMAIL = re.compile(r"\S+@\S+\.\S+")
_URL = re.compile(r"https?://\S+|www\.\S+", re.I)


def chat_day(ts: datetime) -> date:
    return (ts - timedelta(hours=config.DAY_CUT_HOUR)).date()


@dataclass
class Ctx:
    chat: Chat
    names: dict[str, str]
    seed: int
    rng: Rng
    conv_gap: timedelta
    quotes: bool
    spicy: bool

    msgs: list[Message] = field(default_factory=list)
    side: list[str] = field(default_factory=list)
    n: int = 0
    toks: list[list[str]] = field(default_factory=list)
    sq: list[str] = field(default_factory=list)
    convs: list[list[int]] = field(default_factory=list)
    turns: list[list[tuple[str, list[int]]]] = field(default_factory=list)
    reply_events: list[tuple[int, int, str, float, int]] = field(default_factory=list)  # prev_last, first, who, sec, conv
    replies: dict[str, list[float]] = field(default_factory=dict)
    inits: Counter = field(default_factory=Counter)
    inits_after_24h: Counter = field(default_factory=Counter)
    doubles: Counter = field(default_factory=Counter)
    triples: Counter = field(default_factory=Counter)
    last_word: Counter = field(default_factory=Counter)
    msg_count: Counter = field(default_factory=Counter)  # all non-system messages per side
    text_count: Counter = field(default_factory=Counter)
    word_count: Counter = field(default_factory=Counter)
    hour_hist: list[int] = field(default_factory=lambda: [0] * 24)
    hour_by: dict[str, list[int]] = field(default_factory=dict)
    day_of: list[date] = field(default_factory=list)
    day_counts: Counter = field(default_factory=Counter)
    streaks: list[tuple[date, date, int]] = field(default_factory=list)
    silences: list[tuple[int, int]] = field(default_factory=list)
    _proper: set[str] | None = None

    # ---- convenience ----
    def name(self, who: str) -> str:
        return self.names[who]

    @property
    def total_words(self) -> int:
        return sum(self.word_count.values())

    def text_ids(self, who: str | None = None):
        return (i for i, m in enumerate(self.msgs)
                if m.kind == "text" and (who is None or self.side[i] == who))

    def first_date(self) -> date:
        return self.msgs[0].ts.date()

    def last_date(self) -> date:
        return self.msgs[-1].ts.date()

    # ---- quote safety (docs/STATS.md §5.5) ----
    def proper_nouns(self) -> set[str]:
        """Words only ever seen capitalized (likely names), excluding the two participants."""
        if self._proper is None:
            cap, low = set(), set()
            for m in self.msgs:
                if m.kind != "text":
                    continue
                for w in _WORD.findall(_URL.sub(" ", m.text)):
                    (cap if w[0].isupper() else low).add(w.lower())
            mine = {t for nm in self.names.values() for t in tokens(nm)}
            self._proper = cap - low - mine - {"i"}
        return self._proper

    def safe_quote(self, i: int, max_words: int = 6) -> str | None:
        if not self.quotes:
            return None
        m = self.msgs[i]
        t = m.text.strip()
        if m.kind != "text" or not t or len(t.split()) > max_words:
            return None
        if _URL.search(t) or _EMAIL.search(t) or _PHONE.search(t) or _DIGITS.search(t) or "\n" in t:
            return None
        if any(w.lower() in self.proper_nouns() for w in _WORD.findall(t)):
            return None
        if matcher("profanity").search(self.sq[i]):
            return None
        return t


def build_ctx(
    chat: Chat,
    *,
    names: dict[str, str] | None = None,
    swap: bool = False,
    seed: int = 1234,
    conv_gap_hours: float = config.CONV_GAP_HOURS,
    quotes: bool = True,
    spicy: bool = False,
) -> Ctx:
    people = list(chat.participants)
    if len(people) != 2:
        raise ValueError("analysis needs exactly two participants")
    if swap:
        people.reverse()
    sides = {people[0]: A, people[1]: B}
    shown = {A: people[0], B: people[1]}
    if names:
        shown.update({k: v for k, v in names.items() if k in (A, B) and v})
    c = Ctx(chat, shown, seed, Rng(seed), timedelta(hours=conv_gap_hours), quotes, spicy)

    msgs = chat.messages
    c.msgs, c.n = msgs, len(msgs)
    c.side = [sides[m.sender] for m in msgs]
    c.toks = [tokens(m.text) if m.kind == "text" else [] for m in msgs]
    c.sq = [squash(m.text) if m.kind == "text" else "" for m in msgs]
    c.hour_by = {A: [0] * 24, B: [0] * 24}
    c.replies = {A: [], B: []}

    for i, m in enumerate(msgs):
        s = c.side[i]
        c.msg_count[s] += 1
        c.hour_hist[m.ts.hour] += 1
        c.hour_by[s][m.ts.hour] += 1
        if m.kind == "text":
            c.text_count[s] += 1
            c.word_count[s] += len(c.toks[i])
        d = chat_day(m.ts)
        c.day_of.append(d)
        c.day_counts[d] += 1

    # conversations: a gap of at least conv_gap starts a new one
    for i in range(c.n):
        if i and msgs[i].ts - msgs[i - 1].ts < c.conv_gap:
            c.convs[-1].append(i)
        else:
            c.convs.append([i])

    dbl_gap = timedelta(minutes=config.DOUBLE_GAP_MINUTES)
    for ci, conv in enumerate(c.convs):
        first = conv[0]
        c.inits[c.side[first]] += 1
        if first > 0 and msgs[first].ts - msgs[first - 1].ts >= timedelta(hours=24):
            c.inits_after_24h[c.side[first]] += 1
        c.last_word[c.side[conv[-1]]] += 1
        turns: list[tuple[str, list[int]]] = []
        for i in conv:
            if turns and turns[-1][0] == c.side[i]:
                turns[-1][1].append(i)
            else:
                turns.append((c.side[i], [i]))
        c.turns.append(turns)
        for who, idxs in turns:
            gaps = sum(1 for a, b in zip(idxs, idxs[1:]) if msgs[b].ts - msgs[a].ts >= dbl_gap)
            c.doubles[who] += gaps
            c.triples[who] += max(0, gaps - 1)
        for (_, prev), (who, cur) in zip(turns, turns[1:]):
            sec = max((msgs[cur[0]].ts - msgs[prev[-1]].ts).total_seconds(), 0.0)
            c.replies[who].append(sec)
            c.reply_events.append((prev[-1], cur[0], who, sec, ci))

    # active days (both sent a text message) and streaks of calendar-consecutive active days
    sent: dict[date, set[str]] = {}
    for i, m in enumerate(msgs):
        if m.kind == "text":
            sent.setdefault(c.day_of[i], set()).add(c.side[i])
    active = sorted(d for d, s in sent.items() if len(s) == 2)
    for d in active:
        if c.streaks and d - c.streaks[-1][1] == timedelta(days=1):
            c.streaks[-1] = (c.streaks[-1][0], d, c.streaks[-1][2] + 1)
        else:
            c.streaks.append((d, d, 1))

    lim = timedelta(hours=config.SILENCE_HOURS)
    c.silences = [(i, i + 1) for i in range(c.n - 1) if msgs[i + 1].ts - msgs[i].ts >= lim]
    return c
