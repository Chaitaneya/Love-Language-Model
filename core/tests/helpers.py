"""Test-only writers: render a list of messages in every export variant, so the parser can be
round-tripped. Adding a new export format = add a Variant here + a fixture in test_parse.py."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Variant:
    name: str
    family: str  # android | ios
    order: str  # DMY | MDY | YMD
    sep: str = "/"
    year4: bool = False
    h12: bool = False
    seconds: bool = False
    ap_case: str = "lower"  # lower | upper | dots
    ap_space: str = " "
    comma: bool = True
    lrm: bool = False  # prefix each header with U+200E, as iOS does


VARIANTS = [
    Variant("android_dmy_12h", "android", "DMY", h12=True),
    Variant("android_dmy_12h_dots", "android", "DMY", h12=True, ap_case="dots"),
    Variant("android_dmy_24h", "android", "DMY", year4=True),
    Variant("android_mdy_12h", "android", "MDY", h12=True, ap_case="upper"),
    Variant("android_dotted", "android", "DMY", sep="."),
    Variant("android_ymd", "android", "YMD", sep="-", comma=False),
    Variant("ios_dmy_12h", "ios", "DMY", h12=True, seconds=True, ap_case="upper"),
    Variant("ios_dmy_24h", "ios", "DMY", year4=True, seconds=True),
    Variant(
        "ios_mdy_12h_nnbsp", "ios", "MDY", h12=True, seconds=True, ap_case="upper",
        ap_space=" ", lrm=True,
    ),
    Variant("ios_dotted", "ios", "DMY", sep=".", seconds=True),
]


def _date(v: Variant, ts: datetime) -> str:
    day, month = f"{ts.day:02d}", f"{ts.month:02d}"
    if v.order == "YMD":
        return v.sep.join((f"{ts.year:04d}", month, day))
    year = f"{ts.year:04d}" if v.year4 else f"{ts.year % 100:02d}"
    first, second = (day, month) if v.order == "DMY" else (month, day)
    return v.sep.join((first, second, year))


def _time(v: Variant, ts: datetime) -> str:
    hour = (ts.hour % 12 or 12) if v.h12 else ts.hour
    out = f"{hour}:{ts.minute:02d}" if v.h12 else f"{hour:02d}:{ts.minute:02d}"
    if v.seconds:
        out += f":{ts.second:02d}"
    if v.h12:
        am = ts.hour < 12
        ap = {"lower": "am" if am else "pm", "upper": "AM" if am else "PM",
              "dots": "a.m." if am else "p.m."}[v.ap_case]
        out += v.ap_space + ap
    return out


def render_header(v: Variant, ts: datetime) -> str:
    stamp = _date(v, ts) + ("," if v.comma else "") + " " + _time(v, ts)
    head = f"[{stamp}] " if v.family == "ios" else f"{stamp} - "
    return ("‎" if v.lrm else "") + head


def render_chat(v: Variant, messages: list[tuple[datetime, str, str]]) -> str:
    return "".join(f"{render_header(v, ts)}{sender}: {text}\n" for ts, sender, text in messages)
