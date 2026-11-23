"""Free (non-scripted) conversations: who talks, when, and how fast they reply. No text yet."""

from __future__ import annotations

import math
from datetime import date, datetime, time, timedelta

from . import params as P
from .model import Conv, Schedule, Slot, chat_day
from .rng import Rng


def _reply_delay(rng: Rng, replier: str) -> int:
    if replier == P.R:
        d = rng.lognorm(*P.REPLY_R)
    else:
        d = rng.lognorm(*(P.REPLY_T_FAST if rng.chance(P.P_T_FAST) else P.REPLY_T_SLOW))
    return int(min(max(round(d), 2), P.MAX_DELAY))


def _within_turn_gap(rng: Rng, sender: str) -> int:
    if rng.chance(P.P_DOUBLE[sender]):
        d = min(max(rng.lognorm(*P.LONG_GAP), 600), 9000)  # a double text: 10 min .. 2.5 h
    else:
        d = min(max(rng.lognorm(*P.SHORT_GAP), 1), 540)  # always < 10 min
    return int(round(d))


def _turn_length(rng: Rng, sender: str) -> int:
    p = 1.0 / P.TURN_MEAN[sender]
    length = 1 + int(math.log(max(rng.random(), 1e-12)) / math.log(1 - p))
    return min(length, P.TURN_CAP[sender])


def _tempo(cls: str, done: int, n_target: int) -> float:
    """Delay multiplier along a conversation: > 1 at the edges, < 1 in the middle, so night
    conversations are densest around their midpoint (this is what puts the peak hour at 2 AM)."""
    edge, center = P.TEMPO[cls]
    frac = min(done / max(n_target, 1), 1.0)
    return edge - (edge - center) * math.sin(math.pi * frac)


def make_offsets(rng: Rng, initiator: str, n_target: int, cls: str = "A") -> list[tuple[int, str]]:
    """[(seconds since conversation start, sender)] for a free conversation."""
    if initiator == P.R and rng.chance(P.P_PING_CONV):  # a few unanswered pings
        out, t = [(0, P.R)], 0
        for _ in range(rng.randint(0, 2)):
            t += int(min(max(rng.lognorm(*P.SHORT_GAP), 1), 540))
            out.append((t, P.R))
        return out

    out: list[tuple[int, str]] = []
    t, sender = 0, initiator
    while len(out) < n_target:
        for i in range(_turn_length(rng, sender)):
            if out:
                m = _tempo(cls, len(out), n_target)
                if i == 0:
                    t += min(int(_reply_delay(rng, sender) * m), P.MAX_DELAY)
                else:
                    gap = _within_turn_gap(rng, sender)
                    t += gap if gap >= 600 else max(1, min(int(gap * m), 540))  # double texts keep their size
            if t > P.CONV_CAP:
                return out
            out.append((t, sender))
            if len(out) >= n_target:
                break
        sender = P.OTHER[sender]
    return out


def day_multiplier(rng: Rng, day: date) -> float:
    mult = P.MONTH_MULT[(day.year, day.month)]
    if day.weekday() >= 5:
        mult *= P.WEEKEND_MULT
    mult *= rng.lognorm(1.0, 0.22)
    r = rng.random()
    if r < 0.03:
        mult *= 1.8  # a big-talk day
    elif r < 0.07:
        mult *= 0.45  # a quiet day
    return mult


def _day_bounds(day: date) -> tuple[datetime, datetime]:
    d0 = datetime.combine(day, time(0)) + P.DAY_CUT
    end = d0 + timedelta(hours=24) - timedelta(seconds=1)
    if day == P.CHAT_END:  # the chat ends on 23 Oct: nothing after midnight
        end = datetime.combine(day, time(23, 59, 59))
    return d0, end


def fill_days(sched: Schedule, rng: Rng) -> None:
    day = P.CHAT_START
    while day <= P.CHAT_END:
        if day not in sched.tara_zero_days:
            # one stream per day: a parameter change then only perturbs the days it touches,
            # instead of reshuffling everything after it (which made tuning chaotic)
            _fill_day(sched, rng.fork(f"day:{day.isoformat()}"), day)
        day += timedelta(days=1)


def _fill_day(sched: Schedule, rng: Rng, day: date) -> None:
    d0, d_end = _day_bounds(day)
    midnight = datetime.combine(day, time(0))
    mult = day_multiplier(rng, day)
    for cls in ("A", "B", "C"):
        if not rng.chance(P.CLASS_P[cls]):
            continue
        initiator = P.R if rng.chance(P.INITIATOR_ROHAN) else P.T
        n = int(min(max(round(rng.lognorm(P.CLASS_N[cls] * mult, 0.5)), 2), 140))
        w0 = midnight + timedelta(seconds=round(P.CLASS_WINDOW[cls][0] * 3600))  # whole seconds only
        w1 = midnight + timedelta(seconds=round(P.CLASS_WINDOW[cls][1] * 3600))
        for _attempt in range(4):
            offsets = make_offsets(rng, initiator, n, cls)
            dur = timedelta(seconds=offsets[-1][0])
            lo, hi = max(w0, d0), min(w1, d_end - dur)
            prev_end = sched.end_of_conv_before(w1)
            if prev_end is not None:
                lo = max(lo, prev_end + P.MARGIN)
            if lo <= hi:
                start = lo + timedelta(seconds=int(rng.random() * (hi - lo).total_seconds()))
                if sched.fits(start, start + dur):
                    slots = [Slot(start + timedelta(seconds=o), s) for o, s in offsets]
                    sched.add(Conv(slots))
                    break
            n = max(2, int(n * 0.7))


def ensure_active_days(sched: Schedule, base_rng: Rng, skip_days: set[date]) -> int:
    """Every chat day outside the planted gaps gets at least one text from each person, so the
    only broken streaks are the ones we plant. Returns how many messages had to be added."""
    added = 0
    by_day: dict[date, list[Slot]] = {}
    for s in sched.slots():
        by_day.setdefault(chat_day(s.ts), []).append(s)
    day = P.CHAT_START
    while day <= P.CHAT_END:
        slots = by_day.get(day, [])
        if day not in skip_days and day not in sched.tara_zero_days and slots:
            rng = base_rng.fork(f"active:{day.isoformat()}")
            for who in (P.R, P.T):
                if not any(s.sender == who for s in slots):
                    anchor = slots[rng.randint(0, len(slots) - 1)]
                    anchor_conv = next(c for c in sched.convs if anchor in c.slots)
                    i = anchor_conv.slots.index(anchor)
                    nxt = anchor_conv.slots[i + 1].ts if i + 1 < len(anchor_conv.slots) else None
                    room = int((nxt - anchor.ts).total_seconds()) - 1 if nxt else 60
                    if room < 2:
                        continue
                    ts = anchor.ts + timedelta(seconds=rng.randint(1, min(room, 90)))
                    new = Slot(ts, who)
                    anchor_conv.slots.insert(i + 1, new)
                    slots.append(new)
                    added += 1
        day += timedelta(days=1)
    return added
