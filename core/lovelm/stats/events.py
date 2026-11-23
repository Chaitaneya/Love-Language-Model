"""1.7 Milestones and events, 1.8 Spicy."""

from __future__ import annotations

import math
from statistics import median

from ..context import A, B, OTHER, Ctx
from ..text import matcher
from .base import Out, clip, iso, stat, versus


@stat("first_message", "P0", "event", "milestone", "F", charm=0.9)
def first_message(c: Ctx):
    who = c.side[0]
    q = c.safe_quote(0)
    values = {"W": c.name(who), "L": c.name(OTHER[who]), "win": who, "date": iso(c.msgs[0].ts.date())}
    if q:
        values["q"] = q
    return Out(0.8, values, who, [0] if q else [])


@stat("message_milestones", "P1", "event", "milestone", "F", charm=0.85)
def message_milestones(c: Ctx):
    reached = [m for m in (100_000, 50_000, 25_000, 10_000, 5_000, 1_000) if c.n >= m]
    if not reached:
        return None
    quotable = [m for m in reached if c.safe_quote(m - 1)]
    quotable = [m for m in quotable if m >= 5_000] or quotable  # a 1,000th message is a small milestone
    m = quotable[c.rng.fork("milestone").randint(0, len(quotable) - 1)] if quotable else reached[0]
    i = m - 1
    who = c.side[i]
    q = c.safe_quote(i)
    values = {"n": m, "W": c.name(who), "L": c.name(OTHER[who]), "win": who, "date": iso(c.msgs[i].ts.date()), "id": i}
    if q:
        values["q"] = q
    return Out(0.7, values, who, [i] if q else [])


@stat("longest_silence", "P1", "event", "silence", "U", charm=0.8)
def longest_silence(c: Ctx):
    if not c.silences:
        return None
    i, j = max(c.silences, key=lambda p: c.msgs[p[1]].ts - c.msgs[p[0]].ts)
    d = (c.msgs[j].ts.date() - c.msgs[i].ts.date()).days - 1  # whole empty calendar days
    if d < 1:
        return None
    breaker = c.side[j]
    return Out(clip(math.log(max(d, 1) / 0.3) / math.log(20)),
               {"d": d, "W": c.name(breaker), "L": c.name(c.side[i]), "win": breaker, "start": iso(c.msgs[i].ts.date()),
                "end": iso(c.msgs[j].ts.date())}, breaker)


# ---------------------------------------------------------------- spicy (opt-in)
@stat("bang_then_silence", "P1", "event", "silence", "U", spicy=True, charm=1.0)
def bang_then_silence(c: Ctx):
    if (c.last_date() - c.first_date()).days < 14:
        return None
    day, n = c.day_counts.most_common(1)[0]
    later = [d for d in c.day_counts if d > day]
    if not later:
        return None
    d = (min(later) - day).days - 1  # silent chat days right after the busiest day
    if d < 3:
        return None
    return Out(0.95, {"date": iso(day), "n": n, "d": d})


def _lex(c: Ctx, name: str) -> dict[str, int]:
    m = matcher(name)
    cnt = {A: 0, B: 0}
    for i in c.text_ids():
        if m.search(c.sq[i]):
            cnt[c.side[i]] += 1
    return cnt


@stat("apologies", "P1", "versus", "apology", "U", spicy=True, countable="spicy", charm=1.0, n_min=20)
def apologies(c: Ctx):
    cnt = _lex(c, "apology")
    return versus(c, cnt[A], cnt[B]) if cnt[A] + cnt[B] >= 20 else None


@stat("clingy_pings", "P1", "versus", "clingy", "U", spicy=True, charm=0.85, n_min=20)
def clingy_pings(c: Ctx):
    cnt = _lex(c, "ping")
    return versus(c, cnt[A], cnt[B]) if cnt[A] + cnt[B] >= 20 else None


@stat("triple_texts", "P1", "versus", "clingy", "U", spicy=True, charm=0.8, n_min=10)
def triple_texts(c: Ctx):
    a, b = c.triples[A], c.triples[B]
    return versus(c, a, b) if a + b >= 10 else None


@stat("night_starter", "P2", "versus", "clingy", "N", spicy=True, charm=0.5, n_min=10)
def night_starter(c: Ctx):
    cnt = {A: 0, B: 0}
    for conv in c.convs:
        if c.msgs[conv[0]].ts.hour < 5:
            cnt[c.side[conv[0]]] += 1
    return versus(c, cnt[A], cnt[B]) if cnt[A] + cnt[B] >= 10 else None


@stat("silence_breaker", "P1", "event", "silence", "U", spicy=True, charm=0.95)
def silence_breaker(c: Ctx):
    n = len(c.silences)
    if n < 3:
        return None
    cnt = {A: 0, B: 0}
    for _i, j in c.silences:
        cnt[c.side[j]] += 1
    win = A if cnt[A] > cnt[B] else B
    k = cnt[win]
    if k * 2 <= n:
        return None
    return Out(clip((k / n - 0.5) / 0.5) * clip(n / 4),
               {"k": k, "n": n, "W": c.name(win), "L": c.name(OTHER[win]), "win": win, "all": k == n}, win)


@stat("fight_days", "P2", "event", "apology", "U", spicy=True, charm=0.7)
def fight_days(c: Ctx):
    med = median(c.day_counts.values()) if c.day_counts else 0
    if med <= 0:
        return None
    m = matcher("apology")
    first_by = {A: 0, B: 0}
    fights = 0
    for day, n in c.day_counts.items():
        if n < 5 * med:
            continue
        sorry = [i for i in c.text_ids() if c.day_of[i] == day and m.search(c.sq[i])]
        if len(sorry) >= 2:
            fights += 1
            first_by[c.side[sorry[0]]] += 1
    if not fights:
        return None
    return Out(0.8, {"n": fights, "a_first": first_by[A], "b_first": first_by[B], "A": c.name(A), "B": c.name(B)})


@stat("who_is_that", "P2", "versus", "clingy", "N", spicy=True, charm=0.85, n_min=10)
def who_is_that(c: Ctx):
    cnt = _lex(c, "who_is")
    return versus(c, cnt[A], cnt[B]) if cnt[A] + cnt[B] >= 10 else None
