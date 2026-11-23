"""Stage 1 of the build: who talks when. Scenes, free conversations, the 10,000th message and the
exact per-person totals. No message text yet (texts.py fills it in)."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta

from . import convs, scenes
from . import params as P
from .model import Conv, Schedule, Slot, chat_day
from .rng import Rng

TAIL_FROM = datetime(2024, 9, 12)  # per-person totals are balanced using only messages after this date


def build_structure(seed: int):
    rng = Rng(seed)
    sc = scenes.build_scenes(rng.fork("scenes"))
    sched = Schedule()
    scenes.register(sched, sc)
    convs.fill_days(sched, rng.fork("days"))
    convs.ensure_active_days(sched, rng.fork("active"), sc.skip_days)
    fix_message_10000(sched, rng.fork("m10000"))
    balance_totals(sched, rng.fork("balance"), sc)
    slots = sched.slots()
    for i, conv in enumerate(sched.convs):
        conv.id = i
        for s in conv.slots:
            s.conv = i
    return sched, sc, slots


def _plain(s: Slot) -> bool:
    return not s.protected and not s.role


def _insert(conv: Conv, rng: Rng, who: str) -> bool:
    """Add one message from `who` strictly between two existing messages of the conversation."""
    for _ in range(20):
        i = rng.randint(0, len(conv.slots) - 2)
        a, b = conv.slots[i], conv.slots[i + 1]
        gap = int((b.ts - a.ts).total_seconds())
        if gap >= 4:
            conv.slots.insert(i + 1, Slot(a.ts + timedelta(seconds=1 + rng.randint(0, gap - 3)), who))
            return True
    return False


def fix_message_10000(sched: Schedule, rng: Rng) -> None:
    """Message number 10,000 must be a plain message (it becomes Tara's 'wait what', STATS §6.3).
    If a scripted message sits there, nudge the count with one extra early message and look again."""
    early = [c for c in sched.convs if not c.scene and c.start < datetime(2024, 4, 1) and len(c.slots) >= 4]
    for _ in range(200):
        slots = sched.slots()
        s = slots[9999]
        if _plain(s):
            s.sender = P.T
            s.text = P.MESSAGE_10000_WHEN
            s.protected = True
            s.role = "planted"
            s.tags.append("msg_10000")
            return
        _insert(early[rng.randint(0, len(early) - 1)], rng, P.R if rng.chance(0.6) else P.T)
    raise RuntimeError("could not place message 10,000 on a plain message")


def balance_totals(sched: Schedule, rng: Rng, sc: scenes.Scenes) -> None:
    """Make the per-person totals exact (STATS §6.3), touching only the tail months."""
    tail = [c for c in sched.convs if not c.scene and c.start >= TAIL_FROM and len(c.slots) >= 5]
    for who in (P.R, P.T):
        diff = P.TOTAL_BY[who] - sum(1 for s in sched.slots() if s.sender == who)
        if abs(diff) > 900:
            raise RuntimeError(f"timeline is {diff:+d} messages off for {who}; retune CLASS_N")
        while diff > 0:
            if _insert(tail[rng.randint(0, len(tail) - 1)], rng, who):
                diff -= 1
        while diff < 0:
            conv = tail[rng.randint(0, len(tail) - 1)]
            per_day = Counter(chat_day(x.ts) for c in (conv,) for x in c.slots if x.sender == who)
            cand = [x for x in conv.slots[1:] if x.sender == who and _plain(x) and per_day[chat_day(x.ts)] >= 2]
            if len(conv.slots) >= 5 and cand and _day_total(sched, who, chat_day(cand[0].ts)) >= 3:
                victim = cand[rng.randint(0, len(cand) - 1)]
                if _day_total(sched, who, chat_day(victim.ts)) >= 3:
                    conv.slots.remove(victim)
                    diff += 1


def _day_total(sched: Schedule, who: str, day) -> int:
    return sum(1 for c in sched.convs for x in c.slots if x.sender == who and chat_day(x.ts) == day)
