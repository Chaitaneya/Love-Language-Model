"""Public entry points. Bytes in, structured data out; nothing here knows about a browser.

  chat   = load_chat(file_bytes)              parse (and validate) an uploaded export
  result = analyze(chat, seed=1234, ...)      everything the UI shows, as plain JSON-able data

`analyze` is cheap to call again with another seed or toggle (that is what "reroll" does)."""

from __future__ import annotations

from . import config, words
from .charts import charts
from .context import A, B, build_ctx
from .copy import render_stat
from .ingest import read_export
from .meters import assign_archetypes, clingy_meter, love_meter
from .model import Chat
from .parse import parse_chat, validate_chat
from .poster import build_poster
from .rng import Rng
from .stats import run_all

SCHEMA = 1


def load_chat(
    data: bytes,
    *,
    date_order: str | None = None,
    min_messages: int = config.MIN_MESSAGES,
    validate: bool = True,
) -> Chat:
    """Read an uploaded export (.txt or .zip bytes) into a Chat.

    Raises a `lovelm.errors.LoveLMError` subclass (each has a stable `.code`) when the file
    cannot be used. `date_order` ("DMY"/"MDY"/"YMD") overrides detection, e.g. after the UI
    asked the user because `DateOrderAmbiguous` was raised.
    """
    text, warnings = read_export(data)
    chat = parse_chat(text, date_order=date_order)
    chat.warnings[:0] = warnings
    if validate:
        validate_chat(chat, min_messages=min_messages)
    return chat


def analyze(
    chat: Chat,
    *,
    seed: int = 1234,
    spicy: bool = False,
    quotes: bool = True,
    names: dict[str, str] | None = None,
    swap: bool = False,
    conv_gap_hours: float = config.CONV_GAP_HOURS,
) -> dict:
    """Run every stat and build the poster. `names` maps "A"/"B" to nicknames; `swap` exchanges the sides."""
    c = build_ctx(chat, names=names, swap=swap, seed=seed, conv_gap_hours=conv_gap_hours, quotes=quotes, spicy=spicy)
    stats = run_all(c)
    for s in stats:
        s.lines = render_stat(s, c)
    stats.sort(key=lambda s: (-s.rank, s.id))
    arch = assign_archetypes(c, stats)
    ch = charts(c)
    poster = build_poster(c, stats, arch, Rng(seed), ch["heartbeat"]["total"])
    meta = chat.meta
    return {
        "schema": SCHEMA,
        "meta": {
            "format": meta.family, "date_order": meta.date_order, "has_seconds": meta.has_seconds,
            "range": [c.first_date().isoformat(), c.last_date().isoformat()], "messages": c.n,
            "conversations": len(c.convs), "warnings": list(chat.warnings), "spicy": spicy, "quotes": quotes,
            "conv_gap_hours": conv_gap_hours,
        },
        "people": {A: {"name": c.name(A)}, B: {"name": c.name(B)}},
        "stats": [s.to_json() for s in stats],
        "poster": poster,
        "meters": {"love": love_meter(c, stats), **({"clingy": clingy_meter(c, stats)} if spicy else {})},
        "archetypes": arch,
        "words": words.cloud(c),
        "charts": ch,
        "seed": seed,
    }


def analyze_bytes(data: bytes, **options) -> dict:
    """load_chat + analyze in one call (options go to `analyze`)."""
    return analyze(load_chat(data), **options)
