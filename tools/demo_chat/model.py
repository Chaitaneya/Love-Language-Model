"""Generator-side data types: a Slot is one message-to-be, a Conv is a conversation of slots,
and a Schedule keeps conversations apart (>= CONV_GAP) so the parser's conversations are ours."""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from .params import DAY_CUT, MARGIN


@dataclass
class Slot:
    ts: datetime
    sender: str  # "R" | "T"
    text: str = ""
    kind: str = "text"  # text | media | deleted
    media_type: str | None = None
    edited: bool = False
    protected: bool = False  # scenes and planted messages: never touched by balancing or injection
    role: str = ""  # filled by texts.py
    tags: list[str] = field(default_factory=list)
    conv: int = -1


@dataclass
class Conv:
    slots: list[Slot]
    scene: bool = False
    id: int = -1

    @property
    def start(self) -> datetime:
        return self.slots[0].ts

    @property
    def end(self) -> datetime:
        return self.slots[-1].ts


def chat_day(ts: datetime) -> date:
    return (ts - DAY_CUT).date()


class Schedule:
    def __init__(self) -> None:
        self.convs: list[Conv] = []
        self._starts: list[datetime] = []
        self.forbidden: list[tuple[datetime, datetime]] = []  # no message may fall inside [a, b)
        self.tara_zero_days: set[date] = set()  # chat days on which Tara sends nothing

    def add(self, conv: Conv) -> None:
        i = bisect_left(self._starts, conv.start)
        self.convs.insert(i, conv)
        self._starts.insert(i, conv.start)

    def fits(self, start: datetime, end: datetime) -> bool:
        for a, b in self.forbidden:
            if start < b and end >= a:
                return False
        i = bisect_left(self._starts, start)
        if i > 0 and self.convs[i - 1].end + MARGIN > start:
            return False
        if i < len(self.convs) and self.convs[i].start - MARGIN < end:
            return False
        return True

    def end_of_conv_before(self, t: datetime) -> datetime | None:
        i = bisect_right(self._starts, t) - 1
        return self.convs[i].end if i >= 0 else None

    def slots(self) -> list[Slot]:
        out = [s for c in self.convs for s in c.slots]
        out.sort(key=lambda s: s.ts)
        return out


def hours(h: float) -> timedelta:
    return timedelta(seconds=h * 3600)
