"""Normalized text -> Chat. Multi-line messages, system lines, media/deleted/call placeholders."""

from __future__ import annotations

import re

from .config import LOW_MATCH_WARN, MIN_MESSAGES
from .detect import detect_family, resolve_date_order
from .errors import NotTwoPeople, TooFewMessages
from .formats import FAMILIES, Stamp, stamp_from_match, to_datetime
from .lexicon import placeholders
from .model import Chat, ChatMeta, Message, SystemEvent

# "Name: text". A sender never contains ":" or a newline. "Name:" with nothing after is allowed.
_SENDER = re.compile(r"^(?P<sender>[^:\n]{1,80}):(?: (?P<text>.*))?$", re.DOTALL)


def parse_chat(text: str, *, date_order: str | None = None) -> Chat:
    """Parse already-normalized export text (see ingest.read_export)."""
    lines = text.split("\n")
    family, rate = detect_family(lines)
    header = FAMILIES[family]

    blocks: list[tuple[Stamp, list[str]]] = []
    skipped = 0
    for line in lines:
        m = header.match(line)
        if m:
            blocks.append((stamp_from_match(m), [m.group("rest")]))
        elif blocks:
            blocks[-1][1].append(line)  # continuation of a multi-line message
        elif line.strip():
            skipped += 1  # junk before the first header

    stamps = [b[0] for b in blocks]
    order = resolve_date_order(stamps, date_order)

    messages: list[Message] = []
    system: list[SystemEvent] = []
    warnings: list[str] = []
    invalid = 0

    for stamp, body_lines in blocks:
        try:
            ts = to_datetime(stamp, order)
        except ValueError:
            invalid += 1
            continue
        body = "\n".join(body_lines).rstrip()
        sender, msg_text = _split_sender(body)
        if sender is None:
            system.append(SystemEvent(ts=ts, text=body))
            continue
        kind, media_type, edited, msg_text = _classify(msg_text)
        messages.append(
            Message(
                id=len(messages),
                ts=ts,
                sender=sender,
                text=msg_text,
                kind=kind,
                media_type=media_type,
                edited=edited,
            )
        )

    if rate < LOW_MATCH_WARN:
        warnings.append(f"low_header_match_rate:{rate:.2f}")
    if invalid:
        warnings.append(f"dropped_invalid_dates:{invalid}")
    if skipped:
        warnings.append(f"skipped_leading_lines:{skipped}")

    meta = ChatMeta(
        family=family,
        date_order=order,
        hour12=any(s.ap for s in stamps),
        has_seconds=any(s.s is not None for s in stamps),
        header_match_rate=round(rate, 4),
        lines=len(lines),
        skipped_lines=skipped,
    )
    return Chat(messages=messages, system=system, meta=meta, warnings=warnings)


def validate_chat(chat: Chat, *, min_messages: int = MIN_MESSAGES) -> None:
    """Raise NotTwoPeople / TooFewMessages. The product only supports a two-person chat."""
    names = chat.participants
    if len(names) != 2:
        raise NotTwoPeople(f"Expected 2 participants, found {len(names)}.", names=names)
    if len(chat.messages) < min_messages:
        raise TooFewMessages(
            f"Only {len(chat.messages)} messages; need at least {min_messages}.",
            count=len(chat.messages),
        )


def _split_sender(body: str) -> tuple[str | None, str]:
    """(sender, text), or (None, body) for a system line."""
    m = _SENDER.match(body)
    if m is None:
        return None, body
    sender = m.group("sender").strip()
    if not sender or any(rx.search(sender) for rx in placeholders().system_in_sender):
        return None, body
    return sender, (m.group("text") or "").strip()


def _classify(text: str) -> tuple[str, str | None, bool, str]:
    """(kind, media_type, edited, cleaned text)."""
    lex = placeholders()
    edited = False
    for rx in lex.edited_suffix:
        if rx.search(text):
            text = rx.sub("", text).strip()
            edited = True
    probe = text.strip()
    if any(rx.fullmatch(probe) for rx in lex.deleted):
        return "deleted", None, edited, text
    for rx, media_type in lex.media:
        if rx.fullmatch(probe):
            return "media", media_type, edited, text
    if any(rx.fullmatch(probe) for rx in lex.call):
        return "call", None, edited, text
    return "text", None, edited, text
