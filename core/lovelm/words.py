"""Signature words and word-cloud data (docs/STATS.md §2): Fightin' Words, i.e. log-odds with an
informative Dirichlet prior (Monroe, Colaresi & Quinn, 2008)."""

from __future__ import annotations

import math
import re
from collections import Counter

from .context import A, B, Ctx
from .text import emojis, stopwords

ALPHA0 = 500.0
MIN_COUNT = 8
_NUM = re.compile(r"^\d+$")


def tally(c: Ctx, with_emoji: bool = True) -> dict[str, Counter]:
    """Per-side counts of candidate words (stopwords, numbers and one-letter tokens removed) and emoji."""
    stop = stopwords()
    out = {A: Counter(), B: Counter()}
    for i in c.text_ids():
        s = c.side[i]
        out[s].update(w for w in c.toks[i] if w not in stop and len(w) > 1 and not _NUM.match(w))
        if with_emoji:
            out[s].update(emojis(c.msgs[i].text))
    return out


def log_odds(counts: dict[str, Counter], alpha0: float = ALPHA0, min_count: int = MIN_COUNT) -> dict[str, tuple[float, int, int]]:
    """word -> (z, count_A, count_B); z > 0 means A's word, z < 0 means B's."""
    ca, cb = counts[A], counts[B]
    na, nb = sum(ca.values()), sum(cb.values())
    out = {}
    for w in set(ca) | set(cb):
        ya, yb = ca[w], cb[w]
        if ya + yb < min_count:
            continue
        aw = alpha0 * (ya + yb) / (na + nb)
        d = math.log((ya + aw) / (na + alpha0 - ya - aw)) - math.log((yb + aw) / (nb + alpha0 - yb - aw))
        out[w] = (d / math.sqrt(1 / (ya + aw) + 1 / (yb + aw)), ya, yb)
    return out


def signature(c: Ctx, top: int = 5, hide_names: bool = True):
    """(A's top words, B's top words, scores). Probable third-party names are excluded by default."""
    scores = log_odds(tally(c, with_emoji=False))
    hidden = c.proper_nouns() if hide_names else set()
    ranked = sorted(((w, v[0]) for w, v in scores.items() if w not in hidden), key=lambda kv: (kv[1], kv[0]))  # ties by word: sets have no stable order
    return [w for w, _ in ranked[::-1][:top]], [w for w, _ in ranked[:top]], scores


def cloud(c: Ctx, top: int = 40) -> dict:
    counts = tally(c)
    scores = log_odds(counts)
    names = c.proper_nouns()

    def row(w, v):
        return {"w": w, "z": round(v[0], 2), "nA": v[1], "nB": v[2]}

    visible = {w: v for w, v in scores.items() if w not in names}
    a_side = sorted((w for w, v in visible.items() if v[0] >= 2.0), key=lambda w: (-visible[w][0], w))[:top]
    b_side = sorted((w for w, v in visible.items() if v[0] <= -2.0), key=lambda w: (visible[w][0], w))[:top]
    shared = sorted(visible, key=lambda w: (-min(visible[w][1], visible[w][2]), w))
    shared = [w for w in shared if min(visible[w][1], visible[w][2]) >= MIN_COUNT][:top]
    return {
        "dueling": {A: [row(w, visible[w]) for w in a_side], B: [row(w, visible[w]) for w in b_side]},
        "shared": [{"w": w, "nA": visible[w][1], "nB": visible[w][2]} for w in shared],
        "tokens": {A: sum(counts[A].values()), B: sum(counts[B].values())},
        "hidden": [row(w, scores[w]) for w in sorted(names & set(scores), key=lambda w: (-abs(scores[w][0]), w))[:20]],
    }
