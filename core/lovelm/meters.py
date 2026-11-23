"""Meters (docs/STATS.md §3.2-3.4) and archetypes (§3.5). Every meter is a SHARE between the two
partners, built from text behaviours; none of it measures feeling, and the UI says so."""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import median

from .context import A, B, OTHER, Ctx
from .stats.base import Stat


def _share(a: float, b: float) -> float:
    return (a + 1) / (a + b + 2)  # Laplace smoothing


def _by_id(stats: list[Stat]) -> dict[str, Stat]:
    return {s.id: s for s in stats}


# ------------------------------------------------------------------ Love-o-meter
LOVE = [  # key, weight, source stat, minimum total
    ("affection", 0.30, "affection_count", 30), ("initiation", 0.20, "initiator", 20),
    ("reply_speed", 0.15, None, 0), ("words", 0.10, None, 0), ("questions", 0.10, "questions", 100),
    ("compliments", 0.10, "compliments", 15), ("goodnights", 0.05, "goodnight_ritual", 20),
]


def _love_parts(c: Ctx, st: dict[str, Stat]):
    for key, w, sid, _min in LOVE:
        if key == "reply_speed":
            if min(len(c.replies[A]), len(c.replies[B])) >= 100:
                inv = {s: 1 / max(median(c.replies[s]), 1.0) for s in (A, B)}
                yield key, w, inv[A], inv[B], inv[A] / (inv[A] + inv[B])
        elif key == "words":
            if c.total_words >= 5000:
                yield key, w, c.word_count[A], c.word_count[B], _share(c.word_count[A], c.word_count[B])
        elif sid in st:
            a, b = st[sid].values["a"], st[sid].values["b"]
            yield key, w, a, b, _share(a, b)


def _meter(parts) -> dict | None:
    parts = list(parts)
    if not parts:
        return None
    total_w = sum(p[1] for p in parts)
    a = 100 * sum(w * s for _, w, _x, _y, s in parts) / total_w
    return {"A": round(a, 1), "B": round(100 - a, 1),
            "components": [{"key": k, "weight": round(w / total_w, 3), "a": _r(x), "b": _r(y), "share_a": round(s, 3)}
                           for k, w, x, y, s in parts]}


def _r(x):
    return round(x, 4) if isinstance(x, float) else x


def love_meter(c: Ctx, stats: list[Stat]) -> dict | None:
    m = _meter(_love_parts(c, _by_id(stats)))
    if m is None:
        return None
    lead = A if m[A] >= m[B] else B
    gap = abs(m[A] - 50)
    band = "balanced" if gap <= 5 else "lean" if gap <= 15 else "clear"
    w, l = c.name(lead), c.name(OTHER[lead])
    verdict = {
        "balanced": "Perfectly balanced. As all things should be. Suspicious.",
        "lean": f"{w} shows a bit more. {l} is not exactly absent.",
        "clear": f"{w} shows more, in text. That is all this measures.",
    }[band]
    return {**m, "lead": lead, "band": band, "verdict": verdict, "subtitle": "text effort"}


# ------------------------------------------------------------------ Clingy-meter (spicy)
CLINGY = [("double_texts", 0.25), ("pings", 0.20), ("triple_texts", 0.15), ("silence_breaking", 0.15),
          ("apologies", 0.15), ("night_starts", 0.10)]


def clingy_meter(c: Ctx, stats: list[Stat]) -> dict | None:
    st = _by_id(stats)
    own = {s: max(c.msg_count[s], 1) for s in (A, B)}
    raw: dict[str, tuple[float, float]] = {}
    if "double_texts" in st:
        raw["double_texts"] = (c.doubles[A], c.doubles[B])
    if "clingy_pings" in st:
        raw["pings"] = (st["clingy_pings"].values["a"], st["clingy_pings"].values["b"])
    if "triple_texts" in st:
        raw["triple_texts"] = (c.triples[A], c.triples[B])
    if len(c.silences) >= 3:
        k = {A: 0, B: 0}
        for _i, j in c.silences:
            k[c.side[j]] += 1
        raw["silence_breaking"] = (k[A], k[B])
    if "apologies" in st:
        raw["apologies"] = (st["apologies"].values["a"], st["apologies"].values["b"])
    if "night_starter" in st:
        raw["night_starts"] = (st["night_starter"].values["a"], st["night_starter"].values["b"])
    parts = []
    for key, w in CLINGY:
        if key not in raw:
            continue
        ra, rb = (1000 * raw[key][0] / own[A], 1000 * raw[key][1] / own[B])  # per 1,000 of their own messages
        if ra + rb == 0:
            continue
        parts.append((key, w, ra, rb, ra / (ra + rb)))
    m = _meter(parts)
    if m is None:
        return None
    lead = A if m[A] >= m[B] else B
    if abs(m[A] - 50) <= 5:
        labels = {A: "Level: Mutual Chaos", B: "Level: Mutual Chaos"}
    else:
        labels = {lead: "Level: Notification Enthusiast", OTHER[lead]: "Level: Phone Face-Down"}
    return {**m, "lead": lead, "labels": labels, "subtitle": "rates per 1,000 of their own messages"}


# ------------------------------------------------------------------ archetypes
@dataclass(frozen=True)
class Arch:
    name: str
    valence: str
    priority: int  # editorial tie-break: lower is funnier and wins ties between equally extreme people
    blurb: str
    spicy: bool = False


ARCHETYPES = {
    "ghost": Arch("THE GHOST", "U", 1, "Present, in the way weather is present."),
    "double_texter": Arch("THE DOUBLE TEXTER", "N", 2, "Sends the follow-up. Always."),
    "apologist": Arch("THE APOLOGIST", "U", 2, "Sorry. Sorry about that too.", True),
    "pinger": Arch("THE NOTIFICATION ENTHUSIAST", "U", 2, "Has seen your \"last seen\".", True),
    "philosopher": Arch("THE 3 AM PHILOSOPHER", "N", 3, "Deep thoughts, shallow sleep."),
    "romantic": Arch("THE HOPELESS ROMANTIC", "F", 3, "Says it. Out loud. In text."),
    "comedian": Arch("THE COMEDIAN", "F", 3, "Gets the laugh. Counts them."),
    "initiator": Arch("THE INITIATOR", "F", 4, "Someone has to say hi first."),
    "paragraph": Arch("THE PARAGRAPH WRITER", "N", 4, "Texts like they're being billed by the word."),
    "one_word": Arch("THE ONE-WORD WONDER", "N", 4, "\"k\" is a complete thought."),
    "emoji": Arch("THE EMOJI MACHINE", "N", 4, "Nothing said without a face attached."),
    "interviewer": Arch("THE INTERVIEWER", "F", 5, "Asks. Listens. In that order."),
    "last_word": Arch("THE LAST WORD", "N", 5, "The conversation ends when they say so."),
    "reel": Arch("THE REEL DEALER", "N", 5, "Communicates entirely in videos of cats."),
    "voice": Arch("THE VOICE-NOTE ENTHUSIAST", "N", 5, "Why type when you can monologue."),
    "early_bird": Arch("THE EARLY BIRD", "F", 6, "Good morning, unprompted. Disturbing."),
}
LEAD = {A: Arch("THE LEAD", "F", 9, "Two main characters. No supporting cast."),
        B: Arch("THE OTHER LEAD", "F", 9, "Two main characters. No supporting cast.")}


def _ratio(a: float, b: float, side: str, smooth: bool = True) -> float:
    mine, theirs = (a, b) if side == A else (b, a)
    return (mine + 1) / (theirs + 1) if smooth else (mine / theirs if theirs > 0 else 5.0 if mine > 0 else 1.0)


def _score(ratio: float, n: float, n0: float = 60.0) -> float:
    if ratio <= 1:
        return 0.0
    return min(1.0, math.log(ratio) / math.log(5)) * (1 - math.exp(-n / n0))


def archetype_scores(c: Ctx, stats: list[Stat]) -> dict[str, dict[str, float]]:
    """{archetype key: {side: score}}; an archetype missing its data scores 0 for both sides."""
    st = _by_id(stats)
    out: dict[str, dict[str, float]] = {k: {A: 0.0, B: 0.0} for k in ARCHETYPES}

    def versus_arch(key: str, sid: str, *, smooth: bool = True):
        if sid in st:
            a, b = st[sid].values["a"], st[sid].values["b"]
            n = (a + b) if smooth else (c.msg_count[A] + c.msg_count[B])
            for s in (A, B):
                out[key][s] = _score(_ratio(a, b, s, smooth), n)

    versus_arch("double_texter", "double_texts")
    versus_arch("apologist", "apologies")
    versus_arch("pinger", "clingy_pings")
    versus_arch("romantic", "affection_count")
    versus_arch("comedian", "makes_laugh")
    versus_arch("initiator", "initiator")
    versus_arch("interviewer", "questions")
    versus_arch("last_word", "last_word")
    versus_arch("reel", "reel_dealer")
    versus_arch("voice", "voice_notes")
    versus_arch("paragraph", "words_per_message", smooth=False)
    versus_arch("one_word", "one_word_replies", smooth=False)
    versus_arch("emoji", "emoji_per_person", smooth=False)
    versus_arch("early_bird", "early_bird", smooth=False)
    if c.msg_count[A] >= 200 and c.msg_count[B] >= 200:
        night = {s: sum(c.hour_by[s][h] for h in range(5)) / c.msg_count[s] for s in (A, B)}
        for s in (A, B):
            out["philosopher"][s] = _score(night[s] / night[OTHER[s]] if night[OTHER[s]] > 0 else 5.0, c.n)
    if "reply_median" in st and "initiator" in st:
        v, i = st["reply_median"].values, st["initiator"].values
        slow = v["slow_side"]
        init_ratio = _ratio(i["a"], i["b"], OTHER[slow])  # how much more the OTHER one starts
        reply_ratio = v["r"]
        if init_ratio > 1 and reply_ratio > 1:
            out["ghost"][slow] = _score(math.sqrt(reply_ratio * init_ratio), 200)
    return out


def assign_archetypes(c: Ctx, stats: list[Stat]) -> dict:
    scores = archetype_scores(c, stats)
    usable = {k: a for k, a in ARCHETYPES.items() if c.spicy or not a.spicy}

    def claim(side: str, k: str):
        """Strong fits (>= 0.85) are decided by editorial priority, the funniest first: two archetypes that
        both fit a person that well are separated by noise, not by the data. Weaker fits go by score."""
        sc = scores[k][side]
        strong = sc >= 0.85
        return (strong, -usable[k].priority if strong else 0, sc, k)

    def best(side: str, taken: set[str], allowed=None):
        cands = [(claim(side, k), k) for k in usable
                 if k not in taken and scores[k][side] >= 0.25 and (allowed is None or usable[k].valence in allowed)]
        return max(cands) if cands else None

    # pair-wise: take the strongest claim first, then the other person's best remaining archetype
    first = None
    for side in (A, B):
        b = best(side, set())
        if b and (first is None or b > first[0]):
            first = (b, side)
    picks: dict[str, str | None] = {A: None, B: None}
    if first:
        (_, key), side = first
        picks[side] = key
        other = best(OTHER[side], {key})
        picks[OTHER[side]] = other[1] if other else None
    # fairness: two unflattering archetypes are one too many; give the weaker one a kinder fit
    if all(picks[s] and usable[picks[s]].valence == "U" for s in (A, B)):
        weaker = min((A, B), key=lambda s: scores[picks[s]][s])
        alt = best(weaker, {picks[A], picks[B]}, allowed={"F", "N"})
        if alt:
            picks[weaker] = alt[1]
    result = {}
    for s in (A, B):
        arch = usable[picks[s]] if picks[s] else LEAD[s]
        top = sorted(((scores[k][s], k) for k in usable), reverse=True)[:3]
        result[s] = {"key": picks[s] or "lead", "name": arch.name, "blurb": arch.blurb, "valence": arch.valence,
                     "score": round(scores[picks[s]][s], 3) if picks[s] else 0.0,
                     "top": [{"key": k, "name": usable[k].name, "score": round(sc, 3)} for sc, k in top if sc > 0]}
    return result
