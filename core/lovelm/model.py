"""Plain data types. `Message.id` is the index into `Chat.messages`; Exhibit A cites messages by it."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Message:
    id: int
    ts: datetime  # naive, in the exporting phone's local time
    sender: str
    text: str
    kind: str = "text"  # text | media | deleted | call
    media_type: str | None = None  # image | video | audio | sticker | gif | document | contact | media
    edited: bool = False


@dataclass(frozen=True, slots=True)
class SystemEvent:
    ts: datetime
    text: str


@dataclass(frozen=True, slots=True)
class ChatMeta:
    family: str  # android | ios
    date_order: str  # DMY | MDY | YMD
    hour12: bool
    has_seconds: bool
    header_match_rate: float
    lines: int
    skipped_lines: int


@dataclass(slots=True)
class Chat:
    messages: list[Message]
    system: list[SystemEvent]
    meta: ChatMeta
    warnings: list[str] = field(default_factory=list)

    @property
    def participants(self) -> tuple[str, ...]:
        """Distinct senders in order of first appearance."""
        seen: dict[str, None] = {}
        for m in self.messages:
            seen.setdefault(m.sender, None)
        return tuple(seen)
