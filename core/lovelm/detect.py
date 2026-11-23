"""Format detection and date-order resolution (docs/decision.md D14, docs/PRD.md section 11.3)."""

from __future__ import annotations

from datetime import datetime

from .config import DETECT_SAMPLE_LINES, LEADING_JUNK_MAX
from .errors import DateOrderAmbiguous, InconsistentDates, UnrecognizedFormat
from .formats import FAMILIES, ORDERS, Stamp, to_datetime


def detect_family(lines: list[str]) -> tuple[str, float]:
    """Return (family, header_match_rate).

    The family is the grammar of the first header found within the first few non-empty lines
    (a real export starts with one; a stray title line before it is tolerated and skipped later).
    The share of sampled lines that are headers is reported but never blocks: multi-line messages
    legitimately make many lines non-headers. Files that are not chats are caught downstream
    (two participants, enough messages).
    """
    sample: list[str] = []
    for line in lines:
        if line.strip():
            sample.append(line)
            if len(sample) >= DETECT_SAMPLE_LINES:
                break
    if not sample:
        raise UnrecognizedFormat("The file is empty.")

    family = next(
        (name for line in sample[:LEADING_JUNK_MAX] for name, rx in FAMILIES.items() if rx.match(line)),
        None,
    )
    if family is None:
        raise UnrecognizedFormat("This does not look like a WhatsApp chat export.")
    rx = FAMILIES[family]
    return family, sum(1 for line in sample if rx.match(line)) / len(sample)


def _safe(st: Stamp, order: str) -> datetime | None:
    try:
        return to_datetime(st, order)
    except ValueError:
        return None


def _violations(stamps: list[Stamp], order: str) -> tuple[int, list[datetime | None]]:
    """Timestamps are written in order, so the right reading has (almost) no time reversals."""
    parsed = [_safe(s, order) for s in stamps]
    bad, last = 0, None
    for ts in parsed:
        if ts is None:
            bad += 1
            continue
        if last is not None and ts < last:
            bad += 1
        last = ts
    return bad, parsed


def resolve_date_order(stamps: list[Stamp], override: str | None = None) -> str:
    """Return 'DMY', 'MDY' or 'YMD'.

    1. A 4-digit first field means year-first.
    2. A first field > 12 means day-first; a second field > 12 means month-first.
    3. Otherwise count time reversals under each reading and take the lower one.
    4. Still tied and the readings differ: raise DateOrderAmbiguous so the UI can ask once.
    """
    if override is not None:
        if override not in ORDERS:
            raise ValueError(f"date_order must be one of {ORDERS}")
        return override
    if not stamps:
        raise UnrecognizedFormat("No message headers found.")

    if any(s.d1_len == 4 for s in stamps):
        return "YMD"
    first_over = any(s.d1 > 12 for s in stamps)
    second_over = any(s.d2 > 12 for s in stamps)
    if first_over and second_over:
        raise InconsistentDates("Dates have a day in both the first and the second position.")
    if first_over:
        return "DMY"
    if second_over:
        return "MDY"

    dmy_bad, dmy = _violations(stamps, "DMY")
    mdy_bad, mdy = _violations(stamps, "MDY")
    if dmy == mdy:  # e.g. every date is 05/05/..: both readings are the same instant
        return "DMY"
    if dmy_bad != mdy_bad:
        return "DMY" if dmy_bad < mdy_bad else "MDY"

    first = stamps[0]
    raise DateOrderAmbiguous(
        "Dates could be day-first or month-first and the file does not say which.",
        sample=(first.d1, first.d2, first.d3),
        as_dmy=dmy[0].date().isoformat() if dmy[0] else None,
        as_mdy=mdy[0].date().isoformat() if mdy[0] else None,
    )
