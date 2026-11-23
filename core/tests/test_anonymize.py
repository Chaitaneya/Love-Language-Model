"""tools/anonymize_export.py: a real export in, a safe FORMAT sample out.

What has to hold, and is checked here:
  structure   the sample parses to the same structure as the original, in every export variant
  content     no name and no word of the original survives
  quirks      timestamps, iOS's invisible marks, placeholders and the "edited" marker survive byte for byte
  honesty     if the sample would differ from the original, nothing is written
"""

from __future__ import annotations

import io
import random
import re
import unicodedata
import zipfile
from datetime import datetime, timedelta

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

import anonymize_export as A
from conftest import ROOT
from helpers import VARIANTS, Variant, render_chat, render_header
from lovelm.errors import DateOrderAmbiguous, LoveLMError
from lovelm.ingest import read_export
from lovelm.parse import parse_chat
from test_roundtrip import BODY, NAMES

START = datetime(2024, 1, 3, 21, 10, 0)
LATE = datetime(2024, 1, 20, 21, 10, 0)  # a start whose days are all above 12: the date order is never in doubt
ANDROID = Variant("android_dmy_12h", "android", "DMY", h12=True)
IOS = next(v for v in VARIANTS if v.name == "ios_mdy_12h_nnbsp")
WORDS = ["biriyani", "Priya", "Cindy", "headphones", "sunshine", "forgiveness"]


def conversation(n: int = 40, *, start: datetime = START, step_hours: int = 7) -> list[tuple[datetime, str, str]]:
    out = []
    for i in range(n):
        who = "Rohan" if i % 3 else "Tara"
        text = f"{WORDS[i % len(WORDS)]} 123 {WORDS[(i * 2) % len(WORDS)]}, ok? 😭"
        if i % 7 == 0:
            text += f"\nsecond line {WORDS[i % len(WORDS)]}"
        out.append((start + timedelta(hours=step_hours * i), who, text))
    return out


def parse(data: bytes | str, order: str | None = None):
    """Parse without the app's "enough messages, exactly two people" checks, so small samples are fine."""
    data = data.encode() if isinstance(data, str) else data
    return parse_chat(read_export(data)[0], date_order=order)


def shape(data: bytes | str, order: str | None = None):
    """What the parser makes of an export, as plain values: when, who (by order of appearance), what kind,
    how long. If it refuses, the name of its refusal. Written here, apart from the tool's own check."""
    try:
        chat = parse(data, order)
    except LoveLMError as exc:
        return ("error", type(exc).__name__)
    seen: dict[str, int] = {}
    return (
        [(m.ts, seen.setdefault(m.sender, len(seen)), m.kind, len(m.text)) for m in chat.messages],
        [(s.ts, len(s.text)) for s in chat.system],
        chat.meta.family, chat.meta.date_order, chat.meta.hour12,
    )


def words(text: str) -> list[str]:
    return re.findall(r"[^\W\d_]+", text)


# --------------------------------------------------------------------------- structure and content
@pytest.mark.parametrize("variant", VARIANTS, ids=lambda v: v.name)
def test_every_export_variant_keeps_its_structure_and_loses_its_content(variant):
    original = render_chat(variant, conversation()).encode()
    result = A.anonymize(original)

    assert shape(result.text) == shape(original)
    for secret in ["Rohan", "Tara", *WORDS, "second line"]:
        assert secret.lower() not in result.text.lower(), secret
    assert "Person A" in result.text and "Person B" in result.text
    assert result.report.messages_kept == 40 and result.report.senders == 2


@pytest.mark.parametrize("variant", VARIANTS, ids=lambda v: v.name)
def test_headers_are_kept_byte_for_byte(variant):
    msgs = conversation(12)
    heads = [render_header(variant, ts) for ts, _who, _text in msgs]
    lines = A.anonymize(render_chat(variant, msgs).encode()).text.split("\n")
    found, i = [], 0
    for want in heads:  # each header appears, in order, exactly as it was written
        while i < len(lines) and not lines[i].startswith(want):
            i += 1
        assert i < len(lines), f"header not found: {want!r}"
        found.append(lines[i][: len(want)])
        i += 1
    assert found == heads


def test_ios_invisible_marks_and_narrow_spaces_are_really_in_the_fixture_and_survive():
    original = render_chat(IOS, conversation(5))
    assert original.startswith("‎[")  # the variant has iOS's left-to-right mark
    assert any(ord(c) in (0x202F, 0xA0) for c in original) or " " in original
    sample = A.anonymize(original.encode()).text
    o_heads = [ln.split("] ", 1)[0] for ln in original.split("\n") if ln.startswith("‎[")]
    s_heads = [ln.split("] ", 1)[0] for ln in sample.split("\n") if ln.startswith("‎[")]
    assert s_heads == o_heads and len(o_heads) == 5


@settings(max_examples=80, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    variant=st.sampled_from(VARIANTS),
    bodies=st.lists(st.tuples(NAMES, BODY), min_size=2, max_size=12),
    start=st.sampled_from([START, LATE]),  # days all <= 12 (date order unknowable) and days all > 12 (settled)
    step=st.sampled_from([timedelta(minutes=37), timedelta(hours=29)]),
    seed=st.integers(0, 5),
)
def test_property_any_chat_in_any_variant_under_any_date_order(variant, bodies, start, step, seed):
    msgs = [(start + step * i, who, body) for i, (who, body) in enumerate(bodies)]
    original = render_chat(variant, msgs).encode()
    result = A.anonymize(original, seed=seed)
    for order in (None, "DMY", "MDY", "YMD"):  # including the readings the original itself cannot settle
        assert shape(result.text, order) == shape(original, order), order
    # no long word of the original survives (a random 7-letter match has odds of about 1 in 10 billion)
    kept = {w.lower() for w in words(result.text)}
    for _ts, _who, body in msgs:
        for w in words(body):
            assert not (len(w) >= 7 and w.lower() in kept), w


# --------------------------------------------------------------------------- what is WhatsApp's, not yours
def test_placeholders_and_the_edited_marker_are_kept_word_for_word():
    text = "\n".join([
        "03/01/24, 9:10 pm - Rohan: <Media omitted>",
        "03/01/24, 9:11 pm - Tara: This message was deleted",
        "03/01/24, 9:12 pm - Rohan: Missed voice call",
        "03/01/24, 9:13 pm - Tara: image omitted",
        "03/01/24, 9:14 pm - Rohan: I love my secret garden <This message was edited>",
        "03/01/24, 9:15 pm - Tara: ok",
        "",
    ])
    result = A.anonymize(text.encode())
    lines = result.text.split("\n")
    assert lines[:4] == [
        "03/01/24, 9:10 pm - Person A: <Media omitted>",
        "03/01/24, 9:11 pm - Person B: This message was deleted",
        "03/01/24, 9:12 pm - Person A: Missed voice call",
        "03/01/24, 9:13 pm - Person B: image omitted",
    ]
    assert lines[4].endswith(" <This message was edited>") and "secret" not in lines[4]
    assert result.report.placeholders_kept == 4

    chat = parse(result.text, "DMY")  # and the parser still sees what it saw before
    assert [m.kind for m in chat.messages] == ["media", "deleted", "call", "media", "text", "text"]
    assert chat.messages[4].edited


def test_system_lines_keep_wording_that_is_not_personal_and_lose_names():
    text = "\n".join([
        "03/01/24, 9:00 pm - Messages and calls are end-to-end encrypted. No one outside of this chat can read them.",
        "03/01/24, 9:01 pm - Rohan changed the subject to “Goa 2025: the plan”",
        "03/01/24, 9:02 pm - +91 98765 43210 changed their phone number to a new number. Tap to message.",
        "03/01/24, 9:03 pm - Your security code with Tara changed. Tap to learn more.",
        "03/01/24, 9:04 pm - Rohan: hello",
        "03/01/24, 9:05 pm - Tara: hi",
        "",
    ])
    sample = A.anonymize(text.encode()).text
    lines = sample.split("\n")
    assert lines[0] == text.split("\n")[0]  # the generic notice is untouched
    assert "changed the subject" in lines[1] and "Goa" not in lines[1] and "plan" not in lines[1]
    assert "changed their phone number" in lines[2] and "98765" not in lines[2] and "43210" not in lines[2]
    assert "security code" in lines[3] and "Tara" not in lines[3]
    # each is still a system line to the parser, not a message from a person with a strange name
    chat = parse(sample, "DMY")
    assert len(chat.system) == 4 and len(chat.messages) == 2


def test_people_are_numbered_in_order_of_first_appearance_even_in_a_big_group():
    text = "".join(f"03/01/24, 9:{i:02d} pm - Member {i}: hello {i}\n" for i in range(30))
    result = A.anonymize(text.encode())
    assert result.report.senders == 30
    names = [ln.split(" - ")[1].split(":")[0] for ln in result.text.strip().split("\n")]
    assert len(set(names)) == 30 and names[0] == "Person A" and names[25] == "Person Z" and names[26] == "Person 27"


# --------------------------------------------------------------------------- slices and date order
def test_max_messages_keeps_the_first_n_messages():
    result = A.anonymize(render_chat(ANDROID, conversation(40, start=LATE)).encode(), max_messages=10)
    assert result.report.messages_in_original == 40 and result.report.messages_kept == 10
    assert result.text.count("Person") == 10 and not result.report.notes


def test_a_slice_that_cannot_show_its_date_order_gets_one_telling_message():
    # one message a day from 3 Jan: the first ten are all on days <= 12 (DD/MM and MM/DD look the same);
    # the eleventh is the 13th, which settles it
    msgs = conversation(40, step_hours=24)
    assert max(ts.day for ts, *_ in msgs[:10]) <= 12 and msgs[10][0].day == 13
    result = A.anonymize(render_chat(ANDROID, msgs).encode(), max_messages=5)
    assert result.report.messages_kept == 6
    assert any("date order" in note for note in result.report.notes)
    assert parse(result.text).meta.date_order == "DMY"  # the sample can say so by itself
    assert parse(result.text).messages[-1].ts == msgs[10][0]  # the messages in between are the ones left out


def test_a_file_the_parser_rejects_gives_a_sample_that_fails_the_same_way():
    # every message on one day, 3 April or 4 March: nothing in the file can say which
    text = "".join(f"03/04/24, 9:{i:02d} pm - {'Rohan' if i % 2 else 'Tara'}: hi {i}\n" for i in range(20))
    with pytest.raises(DateOrderAmbiguous):
        parse(text)
    result = A.anonymize(text.encode())  # the point: someone with a failing file can still make a safe sample
    assert not result.report.original_parses
    assert any("does not parse" in n for n in result.report.notes)
    with pytest.raises(DateOrderAmbiguous):
        parse(result.text)


# --------------------------------------------------------------------------- input and output forms
def test_a_zip_export_is_read_and_a_bom_is_noticed():
    text = render_chat(ANDROID, conversation(12))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("WhatsApp Chat - Tara/_chat.txt", text)
    assert A.anonymize(buf.getvalue()).report.messages_kept == 12
    assert A.anonymize(b"\xef\xbb\xbf" + text.encode()).had_bom
    assert not A.anonymize(text.encode()).had_bom


def test_not_a_chat_is_a_plain_error():
    with pytest.raises(A.AnonymizeError, match="WhatsApp"):
        A.anonymize(b"hello\nthis is a shopping list\n")
    with pytest.raises(A.AnonymizeError):
        A.anonymize(b"PK\x03\x04 broken")


def test_same_seed_same_sample_other_seed_other_sample():
    data = render_chat(ANDROID, conversation(20)).encode()
    assert A.anonymize(data, seed=1).text == A.anonymize(data, seed=1).text
    assert A.anonymize(data, seed=1).text != A.anonymize(data, seed=2).text


def test_the_demo_couple_loses_every_name_and_keeps_its_shape():
    result = A.anonymize((ROOT / "demo" / "demo_chat.txt").read_bytes(), max_messages=300)
    low = result.text.lower()
    for secret in ["rohan", "tara", "priya", "cindy", "babu"]:
        assert secret not in low
    assert shape(result.text)[3] == "DMY" and result.report.hour12 and result.report.messages_kept == 301


# --------------------------------------------------------------------------- the characters
@given(st.text(max_size=60))
def test_scrambling_is_one_character_for_one_character(text):
    text = A._nfc(text)
    out = A._scramble(text, random.Random(0))
    assert len(out) == len(text)
    for a, b in zip(text, out):
        if unicodedata.category(a)[0] not in "LMN" or A._keep_mark(a):
            assert a == b  # punctuation, spaces, emoji, invisible marks never change
        else:
            assert b.isascii() and b.isalnum()


def test_emoji_stay_whole_and_other_scripts_become_ascii():
    rng = random.Random(0)
    for emoji in ["😭", "❤️", "👨‍👩‍👧", "👍🏽"]:
        assert A._scramble(emoji, rng) == emoji
    keycap = A._scramble("1️⃣", rng)  # the digit is content; the selector and keycap marks are not
    assert keycap[0].isdigit() and keycap[1:] == "1️⃣"[1:]
    hindi = A._scramble("रोहन 42", rng)
    assert hindi.isascii() and len(hindi) == 7 and hindi[4] == " " and hindi[5:].isdigit()
    assert A._scramble("Hello", rng)[0].isupper() and A._scramble("hello", rng).islower()


def test_a_scrambled_line_is_never_accidentally_a_header(monkeypatch):
    calls = []

    def stub(text, rng, protect=None):
        calls.append(text)
        return "03/01/24, 9:10 pm - looks like a header" if len(calls) == 1 else "fine"

    monkeypatch.setattr(A, "_scramble", stub)
    assert A._scramble_free_line("some continuation text", random.Random(0)) == "fine"
    assert len(calls) == 2


# --------------------------------------------------------------------------- the safety net and the command line
def test_nothing_is_written_if_the_sample_would_not_match(tmp_path, monkeypatch, capsys):
    src, dst = tmp_path / "chat.txt", tmp_path / "out.txt"
    src.write_bytes(render_chat(ANDROID, conversation(12)).encode())
    monkeypatch.setattr(A, "_scramble", lambda text, rng, protect=None: text[1:])  # a deliberately broken scrambler
    assert A.main([str(src), "-o", str(dst)]) == 1
    assert not dst.exists()
    assert "Nothing was written" in capsys.readouterr().err


def test_the_command_line(tmp_path, capsys):
    src, dst = tmp_path / "chat.txt", tmp_path / "out.txt"
    original = render_chat(ANDROID, conversation(12)).encode()
    src.write_bytes(original)

    assert A.main([str(src), "-o", str(src)]) == 1  # would overwrite the original
    assert "overwrite your original" in capsys.readouterr().err
    assert src.read_bytes() == original

    assert A.main([str(src), "-o", str(dst)]) == 0
    assert dst.read_text(encoding="utf-8").count("Person") == 12 and src.read_bytes() == original
    err = capsys.readouterr().err
    assert "Checked: the sample parses to the same structure" in err and "Rohan" not in err

    dst.write_text("precious")
    assert A.main([str(src), "-o", str(dst)]) == 1  # exists
    assert dst.read_text() == "precious"
    assert A.main([str(src), "-o", str(dst), "--force"]) == 0
    assert "Person" in dst.read_text()

    assert A.main([str(tmp_path / "missing.txt"), "-o", str(tmp_path / "x.txt")]) == 1
    assert A.main([str(src), "-o", str(tmp_path / "y.txt"), "--max-messages", "-1"]) == 1
