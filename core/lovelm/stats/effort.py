"""1.3 Effort and initiation, 1.4 Replies."""

from __future__ import annotations

from statistics import median

from ..context import A, B, OTHER, Ctx
from .base import Out, clip, iso, stat, versus


@stat("initiator", "P0", "versus", "effort", "F", charm=0.9, n_min=20)
def initiator(c: Ctx):
    a, b = c.inits[A], c.inits[B]
    if a + b < 20:
        return None
    out = versus(c, a, b, extra={})
    if out is None:
        return None
    share = max(a, b) / (a + b)
    out.values.update({"k": round(10 * share), "pct": round(100 * share)})
    return out


@stat("revival", "P1", "versus", "effort", "F", charm=0.7, n_min=8)
def revival(c: Ctx):
    a, b = c.inits_after_24h[A], c.inits_after_24h[B]
    return versus(c, a, b) if a + b >= 8 else None


@stat("longest_monologue", "P0", "event", "effort", "N", charm=1.0)
def longest_monologue(c: Ctx):
    best = (0, None, None, None)  # length, side, indices, reply index
    for turns in c.turns:
        for k, (who, idxs) in enumerate(turns):
            if len(idxs) > best[0]:
                reply = turns[k + 1][1][0] if k + 1 < len(turns) else None
                best = (len(idxs), who, idxs, reply)
    n, who, idxs, reply = best
    if n < 8:
        return None
    values = {"n": n, "W": c.name(who), "L": c.name(OTHER[who]), "win": who,
              "date": iso(c.msgs[idxs[0]].ts.date()), "start_id": idxs[0], "end_id": idxs[-1],
              # how long each message in the run was, in characters (0 for a photo or other media):
              # the poster draws one bar per message at this length, so the picture is the real run
              "lens": [len(c.msgs[i].text) if c.msgs[i].kind == "text" else 0 for i in idxs[:400]]}
    qids: list[int] = []
    if reply is not None:
        q = c.safe_quote(reply)
        values["reply_id"] = reply
        if q:
            values["q"] = q
            qids = [reply]
    return Out(clip((n - 5) / 25), values, who, qids)


@stat("double_texts", "P1", "versus", "effort", "N", countable="spicy", charm=0.85, n_min=50)
def double_texts(c: Ctx):
    a, b = c.doubles[A], c.doubles[B]
    if a + b < 50:
        return None
    return versus(c, a, b, extra={"total": a + b})


@stat("words_per_message", "P1", "versus", "effort", "N", charm=0.6, n_min=200)
def words_per_message(c: Ctx):
    if min(c.text_count.values()) < 200:
        return None
    r = {s: c.word_count[s] / c.text_count[s] for s in (A, B)}
    return versus(c, round(r[A], 1), round(r[B], 1), smooth=False, r_wow=3, n=c.text_count[A] + c.text_count[B])


@stat("one_word_replies", "P2", "versus", "effort", "N", charm=0.6, n_min=200)
def one_word_replies(c: Ctx):
    if min(c.text_count.values()) < 200:
        return None
    short = {A: 0, B: 0}
    for i in c.text_ids():
        if len(c.toks[i]) <= 1:
            short[c.side[i]] += 1
    r = {s: short[s] / c.text_count[s] for s in (A, B)}
    return versus(c, r[A], r[B], smooth=False, r_wow=5, n=c.n, extra={"pct": round(100 * max(r.values()))})


@stat("last_word", "P2", "versus", "effort", "N", charm=0.5, n_min=20)
def last_word(c: Ctx):
    a, b = c.last_word[A], c.last_word[B]
    return versus(c, a, b, r_wow=3, n=a + b) if a + b >= 20 else None


@stat("questions", "P2", "versus", "effort", "F", charm=0.5, n_min=100)
def questions(c: Ctx):
    cnt = {A: 0, B: 0}
    for i in c.text_ids():
        if "?" in c.msgs[i].text:
            cnt[c.side[i]] += 1
    return versus(c, cnt[A], cnt[B], r_wow=3) if cnt[A] + cnt[B] >= 100 else None


# ---------------------------------------------------------------- replies
@stat("reply_median", "P0", "versus", "speed", "U", charm=1.0, n_min=100)
def reply_median(c: Ctx):
    if min(len(c.replies[A]), len(c.replies[B])) < 100:
        return None
    m = {s: median(c.replies[s]) for s in (A, B)}
    out = versus(c, m[A], m[B], lower_is_subject=False, n=min(len(c.replies[A]), len(c.replies[B])) * 2)
    if out is None:
        return None
    slow = A if m[A] > m[B] else B
    fast = OTHER[slow]
    out.subject = slow  # the slower replier is the subject of the joke
    out.values.update({"slow": c.name(slow), "fast": c.name(fast), "sec_slow": round(m[slow]), "sec_fast": round(m[fast]),
                       "sec_a": round(m[A]), "sec_b": round(m[B]), "coarse": not c.chat.meta.has_seconds,
                       "slow_side": slow})
    return out


@stat("reply_fast_share", "P2", "versus", "speed", "F", charm=0.5, n_min=100)
def reply_fast_share(c: Ctx):
    if min(len(c.replies[A]), len(c.replies[B])) < 100:
        return None
    r = {s: sum(1 for x in c.replies[s] if x < 60) / len(c.replies[s]) for s in (A, B)}
    return versus(c, r[A], r[B], smooth=False, r_wow=3, n=len(c.replies[A]) + len(c.replies[B]),
                  extra={"pct": round(100 * max(r.values()))})


@stat("left_hanging", "P2", "versus", "speed", "N", charm=0.6, n_min=10)
def left_hanging(c: Ctx):
    cnt = {A: 0, B: 0}
    for conv in c.convs:
        last = conv[-1]
        if c.msgs[last].kind == "text" and "?" in c.msgs[last].text:
            cnt[c.side[last]] += 1
    return versus(c, cnt[A], cnt[B]) if cnt[A] + cnt[B] >= 10 else None
