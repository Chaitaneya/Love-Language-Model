"""bytes -> clean text. Handles .zip exports (iOS), BOMs, UTF-16, and WhatsApp's invisible characters."""

from __future__ import annotations

import io
import unicodedata
import zipfile

from .config import MAX_ARCHIVE_BYTES
from .errors import BadArchive

_ZIP_MAGIC = b"PK\x03\x04"

# Direction marks and isolates iOS/Android sprinkle into lines. Never U+200D (ZWJ): emoji need it.
_STRIP = dict.fromkeys(
    [0x200E, 0x200F, 0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069, 0xFEFF]
)
# Narrow no-break space (new iOS puts it before AM/PM) and no-break space become plain spaces.
_SPACES = {0x202F: " ", 0x00A0: " "}
_TABLE = {**_STRIP, **_SPACES}


def read_export(data: bytes) -> tuple[str, list[str]]:
    """Return (normalized text, warnings) for an uploaded .txt or .zip export."""
    warnings: list[str] = []
    if data[:4] == _ZIP_MAGIC:
        data = _extract_chat_from_zip(data)
    text = _decode(data, warnings)
    return normalize_text(text), warnings


def normalize_text(text: str) -> str:
    text = text.translate(_TABLE)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return unicodedata.normalize("NFC", text)


def _decode(data: bytes, warnings: list[str]) -> str:
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        warnings.append("decoding_replaced")
        return data.decode("utf-8", errors="replace")


def _extract_chat_from_zip(data: bytes) -> bytes:
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise BadArchive("The file looks like a zip but could not be opened.") from exc
    with zf:
        candidates = [
            i for i in zf.infolist() if not i.is_dir() and i.filename.lower().endswith(".txt")
        ]
        if not candidates:
            raise BadArchive("The zip contains no .txt chat file.")

        def rank(info: zipfile.ZipInfo) -> tuple[int, int]:
            base = info.filename.rsplit("/", 1)[-1].lower()
            if base == "_chat.txt":
                return (0, -info.file_size)
            if "chat" in base:
                return (1, -info.file_size)
            return (2, -info.file_size)

        info = min(candidates, key=rank)
        if info.flag_bits & 0x1:
            raise BadArchive("The zip is password protected.")
        if info.file_size > MAX_ARCHIVE_BYTES:
            raise BadArchive("The chat file inside the zip is too large.", size=info.file_size)
        return zf.read(info)
