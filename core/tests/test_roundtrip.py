"""Property test: any chat written in any supported export variant parses back to itself."""

from __future__ import annotations

import unicodedata
from datetime import datetime, timedelta

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from helpers import VARIANTS, render_chat
from lovelm.api import load_chat

NAMES = st.sampled_from(["Rohan", "Tara", "Babu ❤️", "+91 98765 43210"])
EMOJI = st.sampled_from(["😭", "❤️", "🙂", "👨‍👩‍👧"])
_CHUNK = st.text(
    alphabet=st.one_of(
        st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
        st.sampled_from(list(" .,!?'-():;")),
    ),
    min_size=1,
    max_size=8,
)
# Emoji are multi-codepoint (ZWJ sequences, variation selectors), so they are chunks, not alphabet.
LETTERS = st.lists(st.one_of(_CHUNK, EMOJI), min_size=1, max_size=6).map("".join)
# A continuation line must not look like a header, which always starts with a digit or "[".
LINE = LETTERS.filter(lambda s: not (s[0].isdigit() or s[0] == "["))
BODY = st.lists(LINE, min_size=1, max_size=3).map("\n".join)


@st.composite
def chats(draw):
    n = draw(st.integers(2, 25))
    # The first message falls on day 13-28 so the date order is provable from the data itself.
    first = datetime(
        draw(st.integers(2015, 2033)), draw(st.integers(1, 12)), draw(st.integers(13, 28)),
        draw(st.integers(0, 23)), draw(st.integers(0, 59)), draw(st.integers(0, 59)),
    )
    gaps = draw(st.lists(st.integers(0, 3 * 86400), min_size=n - 1, max_size=n - 1))
    stamps = [first]
    for gap in gaps:
        stamps.append(stamps[-1] + timedelta(seconds=gap))
    senders = draw(st.lists(NAMES, min_size=n, max_size=n))
    bodies = draw(st.lists(BODY, min_size=n, max_size=n))
    return list(zip(stamps, senders, bodies))


@pytest.mark.parametrize("variant", VARIANTS, ids=lambda v: v.name)
@settings(max_examples=120, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(msgs=chats())
def test_roundtrip(variant, msgs):
    text = render_chat(variant, msgs)
    chat = load_chat(text.encode("utf-8"), validate=False)

    expected = [
        (ts if variant.seconds else ts.replace(second=0),
         sender.strip(),
         unicodedata.normalize("NFC", body).strip())
        for ts, sender, body in msgs
    ]
    got = [(m.ts, m.sender, m.text) for m in chat.messages]
    assert got == expected
    assert chat.meta.family == variant.family
    assert chat.meta.date_order == variant.order
    assert chat.meta.hour12 == variant.h12
    assert chat.meta.has_seconds == variant.seconds
    assert chat.system == []
