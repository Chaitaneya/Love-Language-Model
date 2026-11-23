import io
import zipfile

import pytest

from lovelm.api import load_chat
from lovelm.errors import DateOrderAmbiguous, NotTwoPeople, TooFewMessages


def chat_text(senders: list[str], n: int) -> str:
    return "".join(
        f"{13 + i // 50:02d}/01/24, 10:{i % 60:02d} am - {senders[i % len(senders)]}: msg {i}\n"
        for i in range(n)
    )


def test_two_people_enough_messages_passes():
    chat = load_chat(chat_text(["Rohan", "Tara"], 400).encode())
    assert chat.participants == ("Rohan", "Tara") and len(chat.messages) == 400


def test_group_chats_are_rejected():
    with pytest.raises(NotTwoPeople) as err:
        load_chat(chat_text(["Rohan", "Tara", "Cindy"], 400).encode())
    assert err.value.code == "not_two_people" and err.value.data["names"] == ("Rohan", "Tara", "Cindy")


def test_one_sided_chat_is_rejected():
    with pytest.raises(NotTwoPeople):
        load_chat(chat_text(["Rohan"], 400).encode())


def test_trailer_not_a_movie():
    with pytest.raises(TooFewMessages) as err:
        load_chat(chat_text(["Rohan", "Tara"], 299).encode())
    assert err.value.code == "too_few_messages" and err.value.data["count"] == 299


def test_min_messages_and_validation_are_adjustable():
    text = chat_text(["Rohan", "Tara"], 10).encode()
    assert len(load_chat(text, min_messages=5).messages) == 10
    assert len(load_chat(text, validate=False).messages) == 10


def test_zip_end_to_end():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("_chat.txt", chat_text(["Rohan", "Tara"], 400))
        zf.writestr("IMG-1.jpg", b"\xff\xd8")
    chat = load_chat(buf.getvalue())
    assert len(chat.messages) == 400


def test_ingest_warnings_are_kept():
    data = chat_text(["Rohan", "Tara"], 400).encode() + b"\xff"
    assert "decoding_replaced" in load_chat(data).warnings


def test_ambiguous_dates_surface_to_the_caller_and_override_fixes_it():
    text = "".join(
        f"0{3 + i}/04/24, 10:00 am - {'Rohan' if i % 2 == 0 else 'Tara'}: hi\n" for i in range(0, 6, 2)
    ).encode()
    with pytest.raises(DateOrderAmbiguous):
        load_chat(text, validate=False)
    assert load_chat(text, validate=False, date_order="DMY").meta.date_order == "DMY"
