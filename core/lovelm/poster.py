"""Poster selection (docs/STATS.md §4): fill the slots greedily, honour the fairness rule, return JSON.

Order: laurel, top critic, title, tagline, two critics, billing, rating box, fixed lines. (The laurel goes
first so that an equally extreme award stat cannot be spent as a critic quote.)"""

from __future__ import annotations

from .context import A, B, Ctx
from .copy import (CRITIC_SOURCES, FINE_PRINT_FIXED, FINE_PRINT_POOL, REASONS, TAGLINES, TITLES, fmt_date,
                   format_context)
from .rng import Rng
from .stats.base import Stat

CRITIC_MAX = 90
MIN_RANK = 0.2
NOT_CRITIC = {"messages_total", "span_days", "msgs_per_day", "runtime_typing"}  # they have slots of their own
LAUREL = [  # in tie-break order
    ("longest_streak", "WINNER · LONGEST STREAK · {n} DAYS"),
    ("longest_monologue", "WINNER · LONGEST MONOLOGUE · {n} MESSAGES"),
    ("busiest_day", "WINNER · BUSIEST DAY · {n:,} MESSAGES"),
    ("bang_then_silence", "OFFICIAL SELECTION · {n:,} MESSAGES, THEN {d} DAYS OF SILENCE"),
    ("longest_silence", "OFFICIAL SELECTION · THE {d}-DAY SILENCE"),
    ("message_milestones", "OFFICIAL SELECTION · MESSAGE #{n:,}"),
]
LEVELS = ["G", "PG", "PG-13", "R"]


def _join(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def _stars(stat: Stat, c: Ctx, rng: Rng) -> int:
    if stat.valence == "F":
        return 5
    if stat.valence == "N":
        return 4
    return 1 if c.spicy else rng.choice([2, 3])


def _critic_line(stat: Stat, rng: Rng) -> str | None:
    short = [ln for ln in stat.lines if len(ln) <= CRITIC_MAX]
    return rng.choice(short) if short else None


def _source(stat: Stat, c: Ctx, rng: Rng) -> str:
    pool = CRITIC_SOURCES.get(stat.theme, ["Their Phone Battery"])
    return rng.choice(pool).format(A=c.name(A), B=c.name(B))


def build_poster(c: Ctx, stats: list[Stat], archetypes: dict, rng: Rng, heartbeat: list[int]) -> dict:
    by_id = {s.id: s for s in stats}
    ranked = sorted((s for s in stats if s.lines and s.rank >= MIN_RANK), key=lambda s: (-s.rank, -s.score, s.id))
    used_stats: set[str] = set()
    used_themes: set[str] = set()
    unflattering = {A: 0, B: 0}
    limit = 2 if c.spicy else 1

    def take(s: Stat):
        used_stats.add(s.id)
        used_themes.add(s.theme)
        if s.valence == "U" and s.subject in unflattering:
            unflattering[s.subject] += 1

    def fair(s: Stat) -> bool:
        return not (s.valence == "U" and s.subject in unflattering and unflattering[s.subject] >= limit)

    # 1. laurel: the best award-style stat
    laurel = None
    best = None
    for order, (sid, tpl) in enumerate(LAUREL):
        s = by_id.get(sid)
        if s and s.rank >= MIN_RANK and (best is None or (s.rank, -order) > (best[0].rank, -best[1])):
            best = (s, order, tpl)
    if best:
        s, _, tpl = best
        laurel = {"text": tpl.format_map({**format_context(s, c), **s.values}), "stat": s.id}
        take(s)

    # 2. top critic: the best flattering line (countable stats are saved for the rating box)
    def critic_pool(valences):
        return [s for s in ranked if s.id not in used_stats and s.theme not in used_themes and s.id not in NOT_CRITIC
                and not s.countable and s.valence in valences and _critic_line(s, rng.fork("probe:" + s.id))]

    top = None
    for valences in (("F",), ("N",)):
        pool = critic_pool(valences)
        if pool:
            s = pool[0]
            top = {"stars": 5 if s.valence == "F" else 4, "line": _critic_line(s, rng.fork("line:" + s.id)),
                   "source": _source(s, c, rng.fork("src:" + s.id)), "stat": s.id}
            take(s)
            break

    # 3. title
    title = None
    best = None
    for order, (sid, tpl, cond) in enumerate(TITLES):
        s = by_id.get(sid)
        if s and s.id not in used_stats and s.score > 0 and cond(s, c) and (best is None or (round(s.score, 2), -order) > (round(best[0].score, 2), -best[1])):
            best = (s, order, tpl)
    if best:
        s, _, tpl = best
        title = {"text": tpl.format_map({**format_context(s, c), **s.values}).upper(), "stat": s.id}
        used_themes.add(s.theme)  # the title spends its theme, but the stat can still caption a critic line elsewhere

    # 4. tagline
    msgs, days, words = by_id.get("messages_total"), by_id.get("span_days"), c.total_words
    tag_vals = {"messages": c.n, "days": (c.last_date() - c.first_date()).days, "words": round(words, -3),
                "per_day": round(c.n / max((c.last_date() - c.first_date()).days, 1))}
    tagline = rng.fork("tagline").choice(TAGLINES).format_map(tag_vals) if msgs and days else None

    # 5. two critics, one per theme, no more than one unflattering line per person
    critics = []
    alternatives = []
    for s in critic_pool(("F", "N", "U")):
        if not fair(s):
            continue
        line = _critic_line(s, rng.fork("line:" + s.id))
        entry = {"stars": _stars(s, c, rng.fork("stars:" + s.id)), "line": line, "source": _source(s, c, rng.fork("src:" + s.id)),
                 "stat": s.id, "theme": s.theme, "valence": s.valence, "subject": s.subject}
        if len(critics) < 2 and s.theme not in used_themes:
            critics.append(entry)
            take(s)
        else:
            alternatives.append(entry)

    # 6. billing
    billing = [{"side": s, "name": c.name(s).upper(), "archetype": archetypes[s]["name"]} for s in (A, B)]

    # 7. rating box: the strongest countable stats not already spent
    letter = (by_id["swearing"].values["letter"] if "swearing" in by_id else "G")
    if c.spicy:
        letter = LEVELS[min(LEVELS.index(letter) + 1, 3)]
    reasons = []
    for sid, tpl in REASONS.items():
        s = by_id.get(sid)
        if not s or s.id in used_stats or s.score < 0.3:
            continue
        if s.countable == "spicy" and not c.spicy:
            continue
        if s.countable not in ("always", "spicy"):
            continue
        v = {**format_context(s, c), **s.values, "excessive": s.score >= 0.6}
        key = tpl[1:].split("|", 1)[0] if tpl[:1] == "?" else None
        body = tpl.split("|", 1)[1] if key else tpl
        text = body.format_map(v) if (key is None or v.get(key)) else None
        if key and not v.get(key):  # pet name without the 'excessive' flag
            text = f"{v['n']:,} \"{v['token']}\"s"
        reasons.append((s.rank, sid, text))
    reasons = sorted(reasons, key=lambda r: -r[0])[:3]
    order = list(REASONS)
    texts = [t for _, sid, t in sorted(reasons, key=lambda r: order.index(r[1]))]
    if c.spicy:
        texts.append("mild emotional damage")
    rating = {"letter": letter, "reasons": texts,
              "text": f"[{letter}] for {_join(texts)}" if texts else f"[{letter}]"}

    # 8. fixed lines
    pool = [t for t in FINE_PRINT_POOL if not (t.startswith("?double|") and "double_texts" not in by_id)]
    pick = rng.fork("fine").choice(pool)
    pick = pick.split("|", 1)[1] if pick.startswith("?") else pick
    first = c.first_date()
    return {
        "title": title, "tagline": tagline, "laurel": laurel, "top_critic": top, "critics": critics,
        "billing": billing, "release": f"IN CHATS SINCE {first.day} {fmt_date(first.isoformat()).split()[1].upper()} {first.year}",
        "runtime": f"{by_id['runtime_typing'].values['hours']} HRS (OF TYPING)" if "runtime_typing" in by_id else None,
        "rating": rating, "fine_print": [pick.format_map(tag_vals), FINE_PRINT_FIXED],
        "heartbeat": heartbeat, "alternatives": alternatives[:10],
    }
