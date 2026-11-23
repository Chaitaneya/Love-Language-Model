"""1.5 Words and affection, 1.6 Emoji and media."""

from __future__ import annotations

import re
from collections import Counter
from statistics import median

from .. import words as W
from ..context import A, B, OTHER, Ctx
from ..text import emojis, has_url, matcher, phrase_list
from .base import Out, clip, couple_score, iso, stat, versus


def _lex_counts(c: Ctx, name: str) -> dict[str, int]:
    m = matcher(name)
    cnt = {A: 0, B: 0}
    for i in c.text_ids():
        if m.search(c.sq[i]):
            cnt[c.side[i]] += 1
    return cnt


@stat("first_ily", "P0", "event", "milestone", "F", charm=1.0)
def first_ily(c: Ctx):
    m = matcher("i_love_you")
    for i in c.text_ids():
        if m.search(c.sq[i]):
            break
    else:
        return None
    if i == 0:
        return None  # the first message is just a greeting
    who = c.side[i]
    # how fast did the other person answer? (only if they did, inside the same conversation)
    dur = None
    for prev_last, first, replier, sec, ci in c.reply_events:
        if prev_last >= i and replier == OTHER[who] and i in c.convs[ci]:
            dur = round(sec)
            break
    slow = A if median(c.replies[A] or [0]) > median(c.replies[B] or [0]) else B
    days = (c.msgs[i].ts.date() - c.first_date()).days
    return Out(0.9, {"n": days, "W": c.name(who), "L": c.name(OTHER[who]), "win": who, "dur": dur,
                     "date": iso(c.msgs[i].ts.date()), "plot_twist": who == slow and days > 0, "id": i}, who, [i])


@stat("affection_count", "P1", "versus", "affection", "F", charm=0.75, n_min=30)
def affection_count(c: Ctx):
    cnt = _lex_counts(c, "affection")
    return versus(c, cnt[A], cnt[B]) if cnt[A] + cnt[B] >= 30 else None


_GREET = ("love you", "love u", "luv u", "miss you", "miss u", "good morning", "good night", "goodnight", "hi", "hey", "gn", "gm")


def detect_pet_name(c: Ctx) -> tuple[str, int, dict[str, int]] | None:
    """The token that most often follows a love phrase or greeting (>= 20 times), falling back to the
    editable pet-name list. Returns (token, total occurrences, per-side occurrences)."""
    stop = W.stopwords()
    follow: Counter = Counter()
    ends: dict[str, list[list[str]]] = {}
    for g in _GREET:  # index each greeting by its last token, so a message is scanned once, not once per greeting
        gt = g.split()
        ends.setdefault(gt[-1], []).append(gt)
    for i in c.text_ids():
        t = c.toks[i]
        for k in range(len(t) - 1):
            for gt in ends.get(t[k], ()):
                if t[k + 1 - len(gt):k + 1] == gt:
                    nxt = t[k + 1]
                    if nxt not in stop and len(nxt) > 1 and nxt.isalpha():
                        follow[nxt] += 1
    total: Counter = Counter()
    per = {A: Counter(), B: Counter()}
    for i in c.text_ids():
        for w in c.toks[i]:
            total[w] += 1
            per[c.side[i]][w] += 1
    # a pet name follows greetings often, relative to how often it appears at all ("today" does not)
    cands = [w for w, n in follow.most_common() if n >= 20 and n / total[w] >= 0.03]
    if cands:
        best = cands[0]
    else:
        listed = [w for w in phrase_list("pet_names") if total[w] >= 20]
        if not listed:
            return None
        best = max(listed, key=lambda w: total[w])
    return best, total[best], {A: per[A][best], B: per[B][best]}


@stat("pet_name", "P1", "couple", "affection", "F", countable="always", charm=0.9, n_min=20)
def pet_name(c: Ctx):
    r = detect_pet_name(c)
    if r is None:
        return None
    token, n, per = r
    return Out(couple_score(n, 500), {"token": token, "n": n, "a": per[A], "b": per[B]}, n=n)


@stat("compliments", "P2", "versus", "affection", "F", charm=0.6, n_min=15)
def compliments(c: Ctx):
    cnt = _lex_counts(c, "compliment")
    return versus(c, cnt[A], cnt[B]) if cnt[A] + cnt[B] >= 15 else None


@stat("makes_laugh", "P1", "versus", "affection", "F", charm=0.8, n_min=50)
def makes_laugh(c: Ctx):
    m = matcher("laughter")
    cnt = {A: 0, B: 0}
    for _prev, first, replier, sec, _ci in c.reply_events:
        if sec <= 120 and m.search(c.sq[first]):
            cnt[OTHER[replier]] += 1
    return versus(c, cnt[A], cnt[B], r_wow=3) if cnt[A] + cnt[B] >= 50 else None


@stat("ok_period", "P1", "versus", "tone", "U", countable="always", charm=0.95, n_min=5)
def ok_period(c: Ctx):
    cnt = {A: 0, B: 0}
    for i in c.text_ids():
        if c.msgs[i].text.strip().lower() in ("ok.", "okay."):
            cnt[c.side[i]] += 1
    if cnt[A] + cnt[B] < 5:
        return None
    return versus(c, cnt[A], cnt[B], extra={"n": max(cnt.values()), "total": cnt[A] + cnt[B]})


def rating_letter(rate: float) -> str:
    return "G" if rate < 0.5 else "PG" if rate < 2 else "PG-13" if rate < 6 else "R"


@stat("swearing", "P1", "couple", "tone", "N", countable="always", charm=0.5, n_min=5000)
def swearing(c: Ctx):
    words = c.total_words
    if words < 5000:
        return None
    m = matcher("profanity")
    n = sum(m.count(c.sq[i]) for i in c.text_ids())
    rate = 1000 * n / words
    return Out(couple_score(rate, 6) if rate > 0 else 0.0, {"n": n, "rate": round(rate, 2), "letter": rating_letter(rate)}, n=words)


@stat("signature_words", "P0", "versus", "words", "N", charm=0.9, n_min=5000)
def signature_words(c: Ctx):
    if c.total_words < 5000:
        return None
    a, b, scores = W.signature(c, top=5)
    if len(a) < 3 or len(b) < 3:
        return None
    mean_z = (sum(abs(scores[w][0]) for w in a) + sum(abs(scores[w][0]) for w in b)) / (len(a) + len(b))
    return Out(clip(mean_z / 8), {"a": a, "b": b, "A": c.name(A), "B": c.name(B)}, None, n=c.total_words)


# ---------------------------------------------------------------- emoji and media
@stat("emoji_top", "P0", "couple", "emoji", "N", countable="always", charm=0.85, n_min=100)
def emoji_top(c: Ctx):
    cnt: Counter = Counter()
    per = {A: Counter(), B: Counter()}
    for i in c.text_ids():
        for e in emojis(c.msgs[i].text):
            cnt[e] += 1
            per[c.side[i]][e] += 1
    if sum(cnt.values()) < 100:
        return None
    e, n = cnt.most_common(1)[0]
    return Out(couple_score(n, 1500), {"emoji": e, "n": n, "a": per[A][e], "b": per[B][e]}, n=sum(cnt.values()))


@stat("emoji_per_person", "P1", "versus", "emoji", "N", charm=0.7, n_min=100)
def emoji_per_person(c: Ctx):
    per = {A: Counter(), B: Counter()}
    for i in c.text_ids():
        per[c.side[i]].update(emojis(c.msgs[i].text))
    tot = {s: sum(per[s].values()) for s in (A, B)}
    if tot[A] + tot[B] < 100 or min(c.text_count.values()) < 50:
        return None
    r = {s: tot[s] / c.text_count[s] for s in (A, B)}
    top = {s: (per[s].most_common(1)[0][0] if per[s] else "") for s in (A, B)}
    return versus(c, round(r[A], 3), round(r[B], 3), smooth=False, r_wow=3, n=tot[A] + tot[B],
                  extra={"top_a": top[A], "top_b": top[B]})


_REEL = re.compile(r"instagram\.com/(reel|reels|p)/", re.I)


@stat("reel_dealer", "P1", "versus", "media", "N", charm=0.75, n_min=30)
def reel_dealer(c: Ctx):
    cnt = {A: 0, B: 0}
    reels = 0
    for i in c.text_ids():
        if has_url(c.msgs[i].text):
            cnt[c.side[i]] += 1
            reels += bool(_REEL.search(c.msgs[i].text))
    if cnt[A] + cnt[B] < 30:
        return None
    return versus(c, cnt[A], cnt[B], extra={"reels": reels > (cnt[A] + cnt[B]) / 2})


@stat("voice_notes", "P2", "versus", "media", "N", charm=0.7, n_min=20)
def voice_notes(c: Ctx):
    cnt = {A: 0, B: 0}
    for i, m in enumerate(c.msgs):
        if m.media_type == "audio":
            cnt[c.side[i]] += 1
    return versus(c, cnt[A], cnt[B]) if cnt[A] + cnt[B] >= 20 else None  # iOS exports only


@stat("deleted", "P1", "versus", "mystery", "N", countable="always", charm=0.8, n_min=10)
def deleted(c: Ctx):
    cnt = {A: 0, B: 0}
    for i, m in enumerate(c.msgs):
        if m.kind == "deleted":
            cnt[c.side[i]] += 1
    if cnt[A] + cnt[B] < 10:
        return None
    return versus(c, cnt[A], cnt[B], r_wow=3, extra={"n": cnt[A] + cnt[B]})
