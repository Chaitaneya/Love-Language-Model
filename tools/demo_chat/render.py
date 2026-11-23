"""Slots -> an iOS-style WhatsApp export, quirks included (invisible direction marks, narrow no-break
space before AM/PM, multi-line messages, system lines, media/deleted/edited markers)."""

from __future__ import annotations

from datetime import datetime

from . import params as P
from .model import Slot

LRM = "‎"
NNBSP = " "


def stamp(ts: datetime) -> str:
    h12 = ts.hour % 12 or 12
    ap = "AM" if ts.hour < 12 else "PM"
    return f"{ts.day:02d}/{ts.month:02d}/{ts.year % 100:02d}, {h12}:{ts.minute:02d}:{ts.second:02d}{NNBSP}{ap}"


def render(slots: list[Slot], system: list[tuple[datetime, str]]) -> str:
    items: list[tuple[datetime, int, object]] = [(ts, 0, text) for ts, text in system]
    items += [(s.ts, 1, s) for s in slots]
    items.sort(key=lambda it: (it[0], it[1]))
    lines: list[str] = []
    for ts, kind, obj in items:
        if kind == 0:
            lines.append(f"{LRM}[{stamp(ts)}] {obj}")
            continue
        s: Slot = obj  # type: ignore[assignment]
        text = s.text
        if s.kind in ("media", "deleted"):
            text = LRM + text
        if s.edited:
            text += " <This message was edited>"
        lines.append(f"[{stamp(ts)}] {P.NAMES[s.sender]}: {text}")
    return "\n".join(lines) + "\n"
