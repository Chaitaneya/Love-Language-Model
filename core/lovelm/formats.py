"""Message-header grammars (data, not branches) and timestamp conversion.

Two structural families cover WhatsApp exports. Everything else that varies (date order, 12/24h,
separators, seconds) is DETECTED from the file, not enumerated. See docs/decision.md D14.

  android:  31/12/24, 11:59 pm - Name: text
  ios:      [31/12/24, 11:59:58 PM] Name: text
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import NamedTuple

_DATE = r"(?P<d1>\d{1,4})(?P<sep>[/.\-])(?P<d2>\d{1,2})(?P=sep)(?P<d3>\d{1,4})"
_TIME = r"(?P<h>\d{1,2})[:.](?P<mi>\d{2})(?:[:.](?P<s>\d{2}))?"
_AMPM = r"(?:\s?(?P<ap>[AaPp]\.?\s?[Mm]\.?))?"

FAMILIES: dict[str, re.Pattern[str]] = {
    "android": re.compile(rf"^{_DATE},?\s+{_TIME}{_AMPM}\s+-\s(?P<rest>.*)$"),
    "ios": re.compile(rf"^\[{_DATE},?\s+{_TIME}{_AMPM}\]\s(?P<rest>.*)$"),
}

ORDERS = ("DMY", "MDY", "YMD")


class Stamp(NamedTuple):
    """The raw numbers of a header timestamp, before the date order is known."""

    d1: int
    d2: int
    d3: int
    d1_len: int
    d3_len: int
    h: int
    mi: int
    s: int | None
    ap: str | None  # "am" | "pm" | None


def stamp_from_match(m: re.Match[str]) -> Stamp:
    ap = m.group("ap")
    if ap:
        ap = ap.replace(".", "").replace(" ", "").lower()
    s = m.group("s")
    return Stamp(
        int(m.group("d1")),
        int(m.group("d2")),
        int(m.group("d3")),
        len(m.group("d1")),
        len(m.group("d3")),
        int(m.group("h")),
        int(m.group("mi")),
        int(s) if s is not None else None,
        ap,
    )


def to_datetime(st: Stamp, order: str) -> datetime:
    """Convert a Stamp under a date order. Raises ValueError for impossible dates."""
    if order == "DMY":
        day, month, year = st.d1, st.d2, st.d3
    elif order == "MDY":
        month, day, year = st.d1, st.d2, st.d3
    elif order == "YMD":
        year, month, day = st.d1, st.d2, st.d3
    else:
        raise ValueError(f"unknown date order {order!r}")
    if order != "YMD" and st.d3_len <= 2:
        year += 2000
    if not 1990 <= year <= 2100:
        raise ValueError(f"implausible year {year}")

    hour = st.h
    if st.ap is not None:
        if not 1 <= hour <= 12:
            raise ValueError(f"bad 12-hour value {hour}")
        if st.ap == "pm" and hour != 12:
            hour += 12
        elif st.ap == "am" and hour == 12:
            hour = 0
    return datetime(year, month, day, hour, st.mi, st.s or 0)
