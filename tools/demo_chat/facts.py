"""Independent measurements of a chat, written straight from the definitions in docs/STATS.md §1.0.

Deliberately shares no code with the generator: the generator builds toward these numbers and this
module measures them, so an agreement means something. Works on anything with .ts .sender .text
.kind (generator slots or parsed lovelm Messages)."""

from __future__ import annotations

import re
from collections import Counter
from datetime import date, datetime, timedelta
from statistics import median

GAP = timedelta(hours=4)  # CONV_GAP
DOUBLE_GAP = timedelta(minutes=10)
DAY_CUT = timedelta(hours=5)
_TOKEN = re.compile(r"\w+(?:['’]\w+)*")
_URL = re.compile(r"https?://\S+")


def chat_day(ts: datetime) -> date:
    return (ts - DAY_CUT).date()


def conversations(msgs, gap: timedelta = GAP) -> list[list]:
    out: list[list] = []
    for m in msgs:
        if out and m.ts - out[-1][-1].ts < gap:
            out[-1].append(m)
        else:
            out.append([m])
    return out


def turns(conv) -> list[list]:
    out: list[list] = []
    for m in conv:
        if out and out[-1][-1].sender == m.sender:
            out[-1].append(m)
        else:
            out.append([m])
    return out


def reply_seconds(msgs, who, gap: timedelta = GAP) -> list[float]:
    """Seconds from the end of the other person's turn to the start of `who`'s next turn."""
    out: list[float] = []
    for conv in conversations(msgs, gap):
        ts = turns(conv)
        for prev, cur in zip(ts, ts[1:]):
            if cur[0].sender == who:
                out.append(max((cur[0].ts - prev[-1].ts).total_seconds(), 0.0))
    return out


def initiations(msgs, gap: timedelta = GAP) -> Counter:
    return Counter(conv[0].sender for conv in conversations(msgs, gap))


def double_texts(msgs, gap: timedelta = GAP) -> Counter:
    out: Counter = Counter()
    for conv in conversations(msgs, gap):
        for t in turns(conv):
            for a, b in zip(t, t[1:]):
                if b.ts - a.ts >= DOUBLE_GAP:
                    out[b.sender] += 1
    return out


def longest_turn(msgs, gap: timedelta = GAP):
    """(length, turn, the first message of the reply turn or None)."""
    best = (0, [], None)
    for conv in conversations(msgs, gap):
        ts = turns(conv)
        for i, t in enumerate(ts):
            if len(t) > best[0]:
                best = (len(t), t, ts[i + 1][0] if i + 1 < len(ts) else None)
    return best


def hour_histogram(msgs) -> list[int]:
    h = [0] * 24
    for m in msgs:
        h[m.ts.hour] += 1
    return h


def day_counts(msgs) -> Counter:
    return Counter(chat_day(m.ts) for m in msgs)


def active_streaks(msgs, a: str, b: str) -> list[tuple[date, date, int]]:
    """Runs of calendar-consecutive chat days on which BOTH people sent a text message."""
    senders: dict[date, set[str]] = {}
    for m in msgs:
        if m.kind == "text":
            senders.setdefault(chat_day(m.ts), set()).add(m.sender)
    active = sorted(d for d, s in senders.items() if a in s and b in s)
    out: list[tuple[date, date, int]] = []
    for d in active:
        if out and d - out[-1][1] == timedelta(days=1):
            out[-1] = (out[-1][0], d, out[-1][2] + 1)
        else:
            out.append((d, d, 1))
    return out


def silences(msgs, hours: float = 48):
    """[(last message before, first message after)] for every gap of at least `hours`."""
    lim = timedelta(hours=hours)
    return [(x, y) for x, y in zip(msgs, msgs[1:]) if y.ts - x.ts >= lim]


def tokens(text: str) -> list[str]:
    return _TOKEN.findall(_URL.sub(" ", text).lower())


def total_words(msgs) -> int:
    return sum(len(tokens(m.text)) for m in msgs if m.kind == "text")


def summary(msgs, a: str, b: str) -> dict:
    """The banded facts of STATS §6.3 in one dict (for --diagnose and tests)."""
    msgs = list(msgs)
    convs = conversations(msgs)
    init = initiations(msgs)
    dbl = double_texts(msgs)
    hist = hour_histogram(msgs)
    total = len(msgs)
    order = sorted(range(24), key=lambda h: -hist[h])
    streaks = active_streaks(msgs, a, b)
    days = day_counts(msgs)
    busiest = days.most_common(1)[0]
    med = sorted(days.values())[len(days) // 2]
    longest = max(streaks, key=lambda s: s[2]) if streaks else None
    others = sorted((s[2] for s in streaks if s is not longest), reverse=True)
    n_turn, turn, _ = longest_turn(msgs)
    return {
        "messages": total,
        "by_sender": {a: sum(1 for m in msgs if m.sender == a), b: sum(1 for m in msgs if m.sender == b)},
        "conversations": len(convs),
        "convs_per_day": round(len(convs) / max(len(days), 1), 2),
        "initiation_share_a": round(init[a] / max(sum(init.values()), 1), 4),
        "reply_median_s": {a: round(median(reply_seconds(msgs, a))), b: round(median(reply_seconds(msgs, b)))},
        "double_texts": {a: dbl[a], b: dbl[b], "total": dbl[a] + dbl[b]},
        "peak_hour": order[0],
        "hour_share_top3": [(h, round(hist[h] / total, 4)) for h in order[:3]],
        "night_share": round(sum(hist[0:5]) / total, 4),
        "words": total_words(msgs),
        "longest_turn": (n_turn, turn[0].sender if turn else None),
        "busiest_day": (str(busiest[0]), busiest[1], "median_day", med),
        "longest_streak": (str(longest[0]), str(longest[1]), longest[2]) if longest else None,
        "next_longest_streaks": others[:3],
        "silences_48h": len(silences(msgs)),
        "days": len(days),
    }


# ---------------------------------------------------------------- signature words (STATS §2.2)
STOPWORDS = frozenset(
    """a an the i you he she it we they me my your his her our their is are was were be been am to of in on at for
    with and or but so if this that these those there here what when where who how why do did does not no yes ok
    okay just like also too very can will would should could have has had it's i'm you're don't that's i'll let's
    can't i've we'll he's she's what's isn't didn't doesn't won't haha lol hai ka ki ke ko se mein aur ye wo toh
    kya ho hain tha thi ek hi bhi na ya yaar then than as by from up out about into over again one two""".split()
)


def signature_words(msgs, a: str, b: str, alpha0: float = 500.0, min_count: int = 8, top: int = 5):
    """Top words per person by informative-Dirichlet log-odds z-score (Monroe, Colaresi & Quinn 2008)."""
    import math
    ca: Counter = Counter()
    cb: Counter = Counter()
    for m in msgs:
        if m.kind != "text":
            continue
        (ca if m.sender == a else cb).update(w for w in tokens(m.text) if w not in STOPWORDS and len(w) > 1)
    na, nb = sum(ca.values()), sum(cb.values())
    scores = {}
    for w in set(ca) | set(cb):
        ya, yb = ca[w], cb[w]
        if ya + yb < min_count:
            continue
        aw = alpha0 * (ya + yb) / (na + nb)
        d = math.log((ya + aw) / (na + alpha0 - ya - aw)) - math.log((yb + aw) / (nb + alpha0 - yb - aw))
        scores[w] = d / math.sqrt(1.0 / (ya + aw) + 1.0 / (yb + aw))
    ranked = sorted(scores.items(), key=lambda kv: kv[1])
    return ([w for w, _ in ranked[::-1][:top]], [w for w, _ in ranked[:top]], scores)
