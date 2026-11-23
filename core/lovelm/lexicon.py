"""Loads the editable placeholder lexicon (lexicons/placeholders.json)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources

_FLAGS = re.IGNORECASE


@dataclass(frozen=True, slots=True)
class Placeholders:
    media: tuple[tuple[re.Pattern[str], str], ...]
    deleted: tuple[re.Pattern[str], ...]
    call: tuple[re.Pattern[str], ...]
    edited_suffix: tuple[re.Pattern[str], ...]
    system_in_sender: tuple[re.Pattern[str], ...]


@lru_cache(maxsize=1)
def placeholders() -> Placeholders:
    raw = json.loads(
        resources.files("lovelm").joinpath("lexicons/placeholders.json").read_text(encoding="utf-8")
    )

    def comp(items):
        return tuple(re.compile(p, _FLAGS) for p in items)

    return Placeholders(
        media=tuple((re.compile(e["pattern"], _FLAGS), e["type"]) for e in raw["media"]),
        deleted=comp(raw["deleted"]),
        call=comp(raw["call"]),
        edited_suffix=comp(raw["edited_suffix"]),
        system_in_sender=comp(raw["system_in_sender"]),
    )
