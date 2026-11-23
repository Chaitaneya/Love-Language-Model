from datetime import datetime

from lovelm.ingest import normalize_text
from lovelm.parse import parse_chat

ENC = (
    "Messages and calls are end-to-end encrypted. "
    "No one outside of this chat, not even WhatsApp, can read or listen to them."
)


def parse(text: str, **kw):
    return parse_chat(normalize_text(text), **kw)


ANDROID_12H = f"""31/12/23, 11:59 pm - {ENC}
31/12/23, 11:59 pm - Rohan: happy new year babu
01/01/24, 12:00 am - Tara: hmm
01/01/24, 12:01 am - Rohan: line one
line two

line four
13/01/24, 9:05 am - Tara: <Media omitted>
13/01/24, 9:06 am - Rohan: This message was deleted
13/01/24, 12:30 pm - Tara: noon
13/01/24, 12:30 am - Tara: just after midnight
"""


def test_android_12h():
    chat = parse(ANDROID_12H)
    assert chat.meta.family == "android"
    assert chat.meta.date_order == "DMY"  # 13/01 proves day-first
    assert chat.meta.hour12 is True and chat.meta.has_seconds is False
    assert len(chat.system) == 1 and "end-to-end" in chat.system[0].text
    assert [m.sender for m in chat.messages] == ["Rohan", "Tara", "Rohan", "Tara", "Rohan", "Tara", "Tara"]
    assert [m.id for m in chat.messages] == list(range(7))
    assert chat.messages[0].ts == datetime(2023, 12, 31, 23, 59)
    assert chat.messages[1].ts == datetime(2024, 1, 1, 0, 0)  # 12:00 am is midnight
    assert chat.messages[2].text == "line one\nline two\n\nline four"  # multi-line, blank line kept
    assert chat.messages[3].kind == "media" and chat.messages[3].media_type == "media"
    assert chat.messages[4].kind == "deleted"
    assert chat.messages[5].ts.hour == 12  # 12:30 pm is noon
    assert chat.messages[6].ts.hour == 0  # 12:30 am is just after midnight
    assert chat.participants == ("Rohan", "Tara")


def test_ios_24h_with_invisible_marks_and_placeholders():
    lrm = "‎"
    text = (
        f"{lrm}[03/01/24, 21:14:08] Rohan: hi, is this Tara?\n"
        f"{lrm}[03/01/24, 21:15:30] Tara: {lrm}image omitted\n"
        f"{lrm}[04/01/24, 00:02:11] Tara: {lrm}audio omitted\n"
        f"{lrm}[04/01/24, 00:03:00] Rohan: {lrm}sticker omitted\n"
        f"{lrm}[04/01/24, 00:04:00] Rohan: {lrm}Missed voice call\n"
        f"{lrm}[04/01/24, 00:05:00] Tara: this is an edit <This message was edited>\n"
        f"{lrm}[13/01/24, 00:06:00] Tara: {lrm}This message was deleted.\n"
    )
    chat = parse(text)
    assert chat.meta.family == "ios" and chat.meta.has_seconds and not chat.meta.hour12
    kinds = [(m.kind, m.media_type) for m in chat.messages]
    assert kinds == [
        ("text", None), ("media", "image"), ("media", "audio"), ("media", "sticker"),
        ("call", None), ("text", None), ("deleted", None),
    ]
    assert chat.messages[0].text == "hi, is this Tara?"
    assert chat.messages[5].text == "this is an edit" and chat.messages[5].edited
    assert chat.messages[0].ts == datetime(2024, 1, 3, 21, 14, 8)


def test_ios_us_order_with_narrow_nbsp_before_pm():
    text = (
        "[12/31/23, 11:59:58 PM] Rohan: last one\n"
        "[1/2/24, 12:00:03 AM] Tara: first one\n"
    )
    chat = parse(text)
    assert chat.meta.date_order == "MDY"
    assert chat.messages[0].ts == datetime(2023, 12, 31, 23, 59, 58)
    assert chat.messages[1].ts == datetime(2024, 1, 2, 0, 0, 3)


def test_dotted_dates_and_ymd():
    chat = parse("31.12.23, 23:59 - Rohan: a\n01.01.24, 00:01 - Tara: b\n")
    assert chat.meta.date_order == "DMY" and chat.messages[1].ts == datetime(2024, 1, 1, 0, 1)
    chat = parse("2023-12-31 23:59 - Rohan: a\n2024-01-01 00:01 - Tara: b\n")
    assert chat.meta.date_order == "YMD" and chat.messages[1].ts == datetime(2024, 1, 1, 0, 1)


def test_sender_edge_cases():
    text = (
        "13/01/24, 9:05 am - +91 98765 43210: hello\n"
        "13/01/24, 9:06 am - Babu ❤️: note: remember this: ok\n"
        '13/01/24, 9:07 am - Rohan changed the subject to "Plans: now"\n'
        "13/01/24, 9:08 am - Tara changed their phone number to a new number.\n"
        "13/01/24, 9:09 am - Tara:\n"
    )
    chat = parse(text)
    assert chat.participants == ("+91 98765 43210", "Babu ❤️", "Tara")
    assert chat.messages[1].text == "note: remember this: ok"
    assert len(chat.system) == 2  # both change lines are system events, not messages
    assert chat.messages[2].text == ""  # "Tara:" with no text


def test_leading_junk_is_skipped_and_counted():
    chat = parse("some title line\n13/01/24, 9:05 am - Rohan: hi\n13/01/24, 9:06 am - Tara: hey\n"
                 "13/01/24, 9:07 am - Rohan: yo\n13/01/24, 9:08 am - Tara: sup\n"
                 "13/01/24, 9:09 am - Rohan: ok\n13/01/24, 9:10 am - Tara: k\n"
                 "13/01/24, 9:11 am - Rohan: fine\n13/01/24, 9:12 am - Tara: fine\n"
                 "13/01/24, 9:13 am - Rohan: bye\n")
    assert chat.meta.skipped_lines == 1 and "skipped_leading_lines:1" in chat.warnings
    assert len(chat.messages) == 9


def test_mostly_multiline_chat_is_still_recognized_but_flagged():
    # Regression: Hypothesis found that a format check based on the share of header lines rejected
    # valid exports made of long multi-line messages.
    text = "".join(
        f"13/01/24, 9:0{i} am - {'Rohan' if i % 2 == 0 else 'Tara'}: first\nsecond\nthird\nfourth\n"
        for i in range(4)
    )
    chat = parse(text)
    assert len(chat.messages) == 4
    assert chat.messages[0].text == "first\nsecond\nthird\nfourth"
    assert any(w.startswith("low_header_match_rate") for w in chat.warnings)


def test_trailing_blank_lines_do_not_leak_into_last_message():
    chat = parse("13/01/24, 9:05 am - Rohan: hi\n\n\n")
    assert chat.messages[0].text == "hi"
