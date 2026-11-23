"""1.1 Volume, 1.2 Time and rhythm (docs/STATS.md §1)."""

from __future__ import annotations

import math
from collections import Counter

from .. import config
from ..context import A, B, Ctx
from ..text import books, matcher
from .base import Out, clip, couple_score, iso, share_score, stat, versus

NIGHT = range(0, 5)
EARLY = range(5, 9)


def hour_label(h: int) -> str:
    return f"{h % 12 or 12} {'AM' if h < 12 else 'PM'}"


@stat("messages_total", "P0", "couple", "volume", "N", charm=0.5, n_min=300)
def messages_total(c: Ctx):
    return Out(couple_score(c.n, 50_000), {"n": c.n}, n=c.n)


@stat("span_days", "P0", "couple", "volume", "N", charm=0.5)
def span_days(c: Ctx):
    d = (c.last_date() - c.first_date()).days
    if d < 14:
        return None
    return Out(couple_score(d, 730), {"n": d, "start": iso(c.first_date()), "end": iso(c.last_date())})


@stat("msgs_per_day", "P1", "couple", "volume", "N", charm=0.45)
def msgs_per_day(c: Ctx):
    d = (c.last_date() - c.first_date()).days
    if d < 14:
        return None
    v = c.n / d
    return Out(couple_score(v, 100), {"n": round(v)})


@stat("words_total_books", "P1", "couple", "volume", "N", charm=0.9, n_min=5000)
def words_total_books(c: Ctx):
    words = c.total_words
    fits = [b for b in books() if 1.5 <= words / b["words"] <= 12] or [b for b in books() if words / b["words"] >= 1.0]
    if not fits:
        return None
    book = fits[c.rng.fork("book").randint(0, len(fits) - 1)]  # seeded: a reroll can pick another book
    x = words / book["words"]
    return Out(clip(math.log(x) / math.log(4)),
               {"words": round(words, -3), "x": round(x, 1), "book": book["title"], "unit": book["unit"],
                "punch": book["punch"]}, n=words)


@stat("runtime_typing", "P0", "couple", "volume", "N", charm=0.85, n_min=5000)
def runtime_typing(c: Ctx):
    hours = c.total_words / config.WPM / 60
    return Out(couple_score(hours, 200), {"hours": int(hours), "days": round(hours / 24, 1)}, n=c.total_words)


@stat("message_share", "P1", "versus", "effort", "N", charm=0.45, n_min=300)
def message_share(c: Ctx):
    return versus(c, c.msg_count[A], c.msg_count[B], extra={"pct": round(100 * max(c.msg_count.values()) / c.n)})


@stat("peak_hour", "P0", "couple", "time", "N", charm=1.0, n_min=1000)
def peak_hour(c: Ctx):
    if c.n < 1000:
        return None
    h = max(range(24), key=lambda i: c.hour_hist[i])
    share = c.hour_hist[h] / c.n
    s = share_score(share, 0.10, 1 / 24) * (1.0 if h in NIGHT else 0.3)
    return Out(s, {"hour": h, "hour_label": hour_label(h), "share": round(share, 4), "pct": round(100 * share, 1),
                   "night": h in NIGHT}, n=c.n)


@stat("night_owl_share", "P0", "couple", "time", "N", charm=0.7, n_min=500)
def night_owl_share(c: Ctx):
    if c.n < 500:
        return None
    share = sum(c.hour_hist[h] for h in NIGHT) / c.n
    per = {s: sum(c.hour_by[s][h] for h in NIGHT) / max(c.msg_count[s], 1) for s in (A, B)}
    win = A if per[A] > per[B] else B
    return Out(share_score(share, 0.40, 5 / 24),
               {"pct": round(100 * share), "a_pct": round(100 * per[A]), "b_pct": round(100 * per[B]),
                "W": c.name(win), "pct_w": round(100 * per[win]), "win": win}, n=c.n)


@stat("early_bird", "P2", "versus", "time", "F", charm=0.7, n_min=500)
def early_bird(c: Ctx):
    r = {s: sum(c.hour_by[s][h] for h in EARLY) / max(c.msg_count[s], 1) for s in (A, B)}
    if min(c.msg_count.values()) < 100:
        return None
    return versus(c, r[A], r[B], smooth=False, r_wow=5, n=c.n, extra={"pct": round(100 * max(r.values()))})


@stat("longest_streak", "P0", "event", "streak", "F", charm=1.0)
def longest_streak(c: Ctx):
    if not c.streaks:
        return None
    s, e, n = max(c.streaks, key=lambda t: t[2])
    if n < 14:
        return None
    return Out(couple_score(n, 100), {"n": n, "start": iso(s), "end": iso(e)})


@stat("busiest_day", "P1", "event", "volume", "N", charm=0.75)
def busiest_day(c: Ctx):
    if (c.last_date() - c.first_date()).days < 14:
        return None
    day, n = c.day_counts.most_common(1)[0]
    med = sorted(c.day_counts.values())[len(c.day_counts) // 2]
    x = n / max(med, 1)
    return Out(clip(math.log(x) / math.log(10)) if x > 1 else 0.0, {"date": iso(day), "n": n, "x": round(x, 1), "median": med})


@stat("goodnight_ritual", "P2", "versus", "affection", "F", charm=0.6, n_min=20)
def goodnight_ritual(c: Ctx):
    m = matcher("goodnight")
    cnt = Counter(c.side[i] for i in c.text_ids() if m.search(c.sq[i]))
    if cnt[A] + cnt[B] < 20:
        return None
    return versus(c, cnt[A], cnt[B])
