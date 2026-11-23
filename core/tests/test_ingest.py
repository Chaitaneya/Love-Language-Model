import io
import zipfile

import pytest

from lovelm import ingest
from lovelm.errors import BadArchive
from lovelm.ingest import normalize_text, read_export


def make_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_plain_utf8():
    text, warnings = read_export("[03/01/24, 9:14:08 PM] Rohan: hi\n".encode())
    assert text.startswith("[03/01/24") and warnings == []


def test_utf8_bom_is_stripped():
    text, _ = read_export(b"\xef\xbb\xbf" + "hello".encode())
    assert text == "hello"


def test_utf16_with_bom():
    text, _ = read_export("hello 😭".encode("utf-16"))
    assert text == "hello 😭"


def test_invalid_utf8_warns_instead_of_crashing():
    text, warnings = read_export(b"ok \xff\xfe bad")
    assert "decoding_replaced" in warnings
    assert text.startswith("ok ")


def test_invisible_characters_removed_but_zwj_kept():
    family = "👨‍👩‍👧"
    out = normalize_text(f"‎[03/01/24, 9:14:08 PM] Rohan: {family}\r\nnext")
    assert out == f"[03/01/24, 9:14:08 PM] Rohan: {family}\nnext"


def test_nfc_normalization():
    assert normalize_text("é") == "é"


def test_zip_prefers__chat_txt_over_other_files():
    data = make_zip(
        {
            "notes.txt": b"not the chat",
            "_chat.txt": b"[03/01/24, 9:14:08 PM] Rohan: hi",
            "IMG-0001.jpg": b"\xff\xd8\xff",
        }
    )
    text, _ = read_export(data)
    assert "Rohan" in text


def test_zip_with_any_chat_named_txt():
    data = make_zip({"WhatsApp Chat with Tara.txt": b"31/12/23, 11:59 pm - Rohan: hi"})
    text, _ = read_export(data)
    assert "Rohan" in text


def test_zip_without_txt_is_rejected():
    with pytest.raises(BadArchive):
        read_export(make_zip({"a.jpg": b"x"}))


def test_corrupt_zip_is_rejected():
    with pytest.raises(BadArchive):
        read_export(b"PK\x03\x04 this is not really a zip")


def test_oversized_member_is_rejected(monkeypatch):
    monkeypatch.setattr(ingest, "MAX_ARCHIVE_BYTES", 10)
    with pytest.raises(BadArchive):
        read_export(make_zip({"_chat.txt": b"x" * 100}))
