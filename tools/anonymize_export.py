#!/usr/bin/env python3
"""Turn a real WhatsApp export into a FORMAT SAMPLE that is safe to read, keep as a test fixture, or paste
into a bug report. Standard library only (plus the lovelm core next to it).

  python3 tools/anonymize_export.py "WhatsApp Chat with X.txt" -o sample.txt
  python3 tools/anonymize_export.py export.zip -o sample.txt --max-messages 0     # 0 = keep every message

What it KEEPS, because the parser's behaviour depends on it:
  every timestamp exactly as written (the date-order inference needs the real numbers), who spoke in what
  order, how long every message is, punctuation, whitespace, emoji, invisible marks (iOS's U+200E, the
  narrow no-break space), multi-line structure, and WhatsApp's own placeholders ("<Media omitted>",
  "This message was deleted", call lines, the "<This message was edited>" suffix).
What it CHANGES: every name (Person A, Person B, ...) and every letter and digit of every message,
  system line and stray line, replaced with random ones of the same kind ("hello 42" -> "qvzgt 07").

So it is a sample of the format, not of the conversation: the stats will not mean anything on it. And it is
not magic. Your timestamps are still there (they show WHEN you talked), and so are message lengths. Read the
output before you share it.

Before writing anything it parses the original and the sample and checks that they come out the same
(same count, same times, same speaker order, same lengths, same kinds; and if the original does not parse,
that the sample fails in the same way, so a bug report still reproduces). If they differ, nothing is written.
It never changes your original file and will not overwrite anything unless you say --force.
"""

from __future__ import annotations

import argparse
import random
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
try:
    import lovelm  # noqa: F401
except ImportError:  # running from a checkout, not an installed package
    sys.path.insert(0, str(ROOT / "core"))

# The tool shares the parser's own logic (header grammars, who-is-the-sender, what is a placeholder) so it can
# never disagree with it. A few of those helpers are module-private by convention; coupling to them is
# deliberate, and test_anonymize.py fails if they drift.
from lovelm.detect import detect_family  # noqa: E402
from lovelm.errors import LoveLMError  # noqa: E402
from lovelm.formats import FAMILIES  # noqa: E402
from lovelm.ingest import _SPACES, _STRIP, _decode, _extract_chat_from_zip  # noqa: E402
from lovelm.lexicon import placeholders  # noqa: E402
from lovelm.parse import _classify, _split_sender, parse_chat  # noqa: E402

DEFAULT_MAX_MESSAGES = 300
_UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_LOWER = "abcdefghijklmnopqrstuvwxyz"
_DIGITS = "0123456789"
_ZIP_MAGIC = b"PK\x03\x04"
# Generic WhatsApp system lines that carry no personal data, kept word for word.
_GENERIC_SYSTEM = (re.compile(r"messages (and calls )?are end-to-end encrypted\b.*", re.I | re.S),)


class AnonymizeError(Exception):
    """Something the user can act on (not a bug): unreadable input, or a sample that would not match."""


@dataclass
class Report:
    family: str = ""
    date_order: str | None = None
    hour12: bool = False
    seconds: bool = False
    messages_in_original: int = 0
    messages_kept: int = 0
    system_blocks_kept: int = 0
    placeholders_kept: int = 0
    senders: int = 0
    leading_junk_lines: int = 0
    original_parses: bool = True
    notes: list[str] = field(default_factory=list)


@dataclass
class Anonymized:
    text: str
    report: Report
    had_bom: bool


# ----------------------------------------------------------------------------- characters
def _norm_char(c: str) -> str:
    """What lovelm's normalisation turns this character into ("" = removed)."""
    o = ord(c)
    if o in _STRIP:
        return ""
    return _SPACES.get(o, c)


def _normalized(raw: str) -> tuple[str, list[int]]:
    """The line as the parser sees it, and for each of its characters the index it came from in `raw`."""
    out, idx = [], []
    for i, c in enumerate(raw):
        n = _norm_char(c)
        if n:
            out.append(n)
            idx.append(i)
    return "".join(out), idx


def _keep_mark(c: str) -> bool:
    """Marks that make emoji emoji (variation selectors, keycap) are not content."""
    return 0xFE00 <= ord(c) <= 0xFE0F or ord(c) == 0x20E3


def _swap(c: str, rng: random.Random) -> str:
    cat = unicodedata.category(c)
    if cat[0] == "N":
        return rng.choice(_DIGITS)
    if cat[0] == "L" or (cat[0] == "M" and not _keep_mark(c)):
        return rng.choice(_UPPER) if c.isupper() else rng.choice(_LOWER)
    return c  # punctuation, spaces, symbols, emoji, invisible marks


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _scramble(text: str, rng: random.Random, protect: list[tuple[int, int]] | None = None) -> str:
    """Replace letters, digits and marks, one character for one character. `protect` = index ranges to leave.
    `text` should already be NFC (see _nfc), so that those indexes still point at the same characters."""
    protect = protect or []
    return "".join(c if any(a <= i < b for a, b in protect) else _swap(c, rng) for i, c in enumerate(text))


def _looks_like_header(line: str) -> bool:
    n, _ = _normalized(line)
    return any(rx.match(n) for rx in FAMILIES.values())


def _scramble_free_line(line: str, rng: random.Random) -> str:
    """A line that is not a header must not become one by accident (letters could spell "pm")."""
    line = _nfc(line)
    for _ in range(50):
        out = _scramble(line, rng)
        if not _looks_like_header(out):
            return out
    return "x" + _scramble(line, rng)[1:]  # cannot happen in practice; keeps the guarantee anyway


def _protected_spans(raw: str, patterns) -> list[tuple[int, int]]:
    """Index ranges in `raw` matching any regex (which was written against the normalised line)."""
    n, idx = _normalized(raw)
    spans = []
    for rx in patterns:
        for m in rx.finditer(n):
            if m.end() > m.start():
                spans.append((idx[m.start()], idx[m.end() - 1] + 1))
    return spans


# ----------------------------------------------------------------------------- the blocks
@dataclass
class _Block:
    head: str  # the header text exactly as written, up to where the message starts
    lines: list[str]  # raw message lines: the first follows the header, the rest are continuations


def _split(raw_lines: list[str], family: str) -> tuple[list[str], list[_Block]]:
    rx = FAMILIES[family]
    junk: list[str] = []
    blocks: list[_Block] = []
    for raw in raw_lines:
        n, idx = _normalized(raw)
        m = rx.match(n)
        if m:
            start = m.start("rest")
            cut = idx[start] if start < len(idx) else len(raw)
            blocks.append(_Block(head=raw[:cut], lines=[raw[cut:]]))
        elif blocks:
            blocks[-1].lines.append(raw)
        elif raw.strip():
            junk.append(raw)
    return junk, blocks


def _body(block: _Block) -> str:
    """The block as the parser reads it: normalised, lines joined, trailing space trimmed."""
    return "\n".join(_normalized(line)[0] for line in block.lines).rstrip()


def _first_telling_block(blocks: list[_Block], start: int, family: str, order: str) -> int | None:
    """Index of the first block at or after `start` whose day-of-month is above 12 (it settles DMY vs MDY)."""
    day = {"DMY": "d1", "MDY": "d2", "YMD": "d3"}[order]
    rx = FAMILIES[family]
    for i in range(start, len(blocks)):
        m = rx.match(_normalized(blocks[i].head + blocks[i].lines[0])[0])
        if m and int(m.group(day)) > 12:
            return i
    return None


def _pseudonym(i: int) -> str:
    return f"Person {_UPPER[i]}" if i < 26 else f"Person {i + 1}"


def _is_blank(c: str) -> bool:
    n = _norm_char(c)
    return n == "" or n.isspace()


def _anonymize_block(block: _Block, names: dict[str, str], rng: random.Random, rep: Report) -> _Block:
    body = _body(block)
    sender, text = _split_sender(body)
    lex = placeholders()

    if sender is None:  # a system line
        rep.system_blocks_kept += 1
        if any(rx.fullmatch(body) for rx in _GENERIC_SYSTEM):
            return block
        # Words that make the parser treat it as a system line ("changed the subject") are not personal;
        # everything else (names, a group's subject, phone numbers) is.
        out = []
        for i, line in enumerate(block.lines):
            line = _nfc(line)
            scrambled = _scramble(line, rng, _protected_spans(line, lex.system_in_sender))
            out.append(_scramble_free_line(line, rng) if i and _looks_like_header(scrambled) else scrambled)
        return _Block(block.head, out)

    pseudo = names.setdefault(sender, _pseudonym(len(names)))
    first = _nfc(block.lines[0])
    colon = first.index(":")  # the sender never contains one, so the first colon ends the name
    raw_name = first[:colon]
    lead = next((i for i, c in enumerate(raw_name) if not _is_blank(c)), len(raw_name))
    trail = next((i for i, c in enumerate(reversed(raw_name)) if not _is_blank(c)), len(raw_name))
    name_part = raw_name[:lead] + pseudo + (raw_name[len(raw_name) - trail:] if trail and lead < len(raw_name) else "")

    kind, _media, _edited, _clean = _classify(text)
    if kind != "text":  # media / deleted / call placeholders are WhatsApp's words, not the user's
        rep.placeholders_kept += 1
        return _Block(block.head, [name_part + first[colon:], *block.lines[1:]])

    # the text, line by line; the first line starts at the colon (which is not a letter, so it stays)
    parts = [first[colon:], *[_nfc(line) for line in block.lines[1:]]]
    # "<This message was edited>" is WhatsApp's, and sits on the last line that has anything on it
    last = max((i for i, part in enumerate(parts) if _normalized(part)[0].strip()), default=0)
    keep = _protected_spans(parts[last], lex.edited_suffix)
    out = []
    for i, part in enumerate(parts):
        scrambled = _scramble(part, rng, keep if i == last else None)
        if i and _looks_like_header(scrambled):
            scrambled = _scramble_free_line(part, rng)
        out.append(name_part + scrambled if i == 0 else scrambled)
    return _Block(block.head, out)


# ----------------------------------------------------------------------------- verification
def _signature(chat):
    seen: dict[str, int] = {}
    msgs = [
        (m.ts, seen.setdefault(m.sender, len(seen)), m.kind, m.media_type, m.edited, len(m.text))
        for m in chat.messages
    ]
    system = [(s.ts, len(s.text)) for s in chat.system]
    meta = chat.meta
    return (msgs, system, meta.family, meta.date_order, meta.hour12, meta.has_seconds, tuple(chat.warnings))


def _outcome(text: str, order: str | None):
    """What the parser does with this text: its structure, or the kind of error it raises."""
    from lovelm.ingest import normalize_text

    try:
        return ("parsed", _signature(parse_chat(normalize_text(text), date_order=order)))
    except LoveLMError as exc:
        return ("error", type(exc).__name__)


def _verify(original: str, sample: str, order: str | None) -> None:
    """The sample must parse exactly like the original. If the original's date order is not settled (an ambiguous
    file, or one that fails), "both raise the same error" would prove nothing about the text, so every order the
    reader might pick is compared too: the full structure, not just the error name."""
    orders = (None, order) if order else (None, "DMY", "MDY", "YMD")
    for forced in orders:
        a, b = _outcome(original, forced), _outcome(sample, forced)
        if a != b:
            raise AnonymizeError(
                "The anonymised sample does not parse the same way as your original"
                f" (date order {forced or 'inferred'}): original {a[0]}"
                f"{' (' + a[1] + ')' if a[0] == 'error' else ''}, sample {b[0]}"
                f"{' (' + b[1] + ')' if b[0] == 'error' else ''}. Nothing was written. Please report this: it is a bug in the tool."
            )


# ----------------------------------------------------------------------------- the public function
def anonymize(data: bytes, *, seed: int = 0, max_messages: int | None = None) -> Anonymized:
    """bytes of a .txt or .zip export -> an Anonymized sample (or AnonymizeError)."""
    had_bom = data[:3] == b"\xef\xbb\xbf"
    try:
        if data[:4] == _ZIP_MAGIC:
            data = _extract_chat_from_zip(data)
            had_bom = data[:3] == b"\xef\xbb\xbf"
        text = _decode(data, [])
    except LoveLMError as exc:
        raise AnonymizeError(str(exc)) from exc
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    raw_lines = text.split("\n")

    try:
        family, _rate = detect_family([_normalized(line)[0] for line in raw_lines])
    except LoveLMError as exc:
        raise AnonymizeError(f"{exc} Is this a WhatsApp export (Export chat, then Without media)?") from exc

    rng = random.Random(seed)
    junk, blocks = _split(raw_lines, family)
    rep = Report(family=family, leading_junk_lines=len(junk))
    names: dict[str, str] = {}

    # keep the first `max_messages` messages, and the system lines before the first one dropped
    is_message = [_split_sender(_body(b))[0] is not None for b in blocks]
    rep.messages_in_original = sum(is_message)
    cut, seen = len(blocks), 0
    if max_messages:
        for i, flag in enumerate(is_message):
            seen += flag
            if flag and seen > max_messages:
                cut = i
                break
    keep = list(range(cut))
    full = _outcome(text, None)
    rep.original_parses = full[0] == "parsed"
    if rep.original_parses:
        _msgs, _sys, _fam, rep.date_order, rep.hour12, rep.seconds, _warn = full[1]
    else:
        rep.notes.append(f"Your original does not parse ({full[1]}); the sample fails in exactly the same way.")

    def original_of(indexes: list[int]) -> str:
        lines = list(junk)
        for i in indexes:
            lines += [blocks[i].head + blocks[i].lines[0], *blocks[i].lines[1:]]
        return "\n".join(lines).rstrip("\n") + "\n"

    # A slice of a file whose first days are all <= 12 cannot show its own date order, and that is the
    # hardest thing about these formats. If the full file settles it, keep the first later message that does too.
    if rep.date_order in ("DMY", "MDY", "YMD") and cut < len(blocks) and _outcome(original_of(keep), None) == ("error", "DateOrderAmbiguous"):
        extra = _first_telling_block(blocks, cut, family, rep.date_order)
        if extra is not None:
            keep.append(extra)
            rep.notes.append(
                "Added one later message (a day above 12) so the sample can show its own date order; "
                "the messages in between are left out."
            )

    out_blocks = [_anonymize_block(blocks[i], names, rng, rep) for i in keep]
    rep.messages_kept = sum(is_message[i] for i in keep)
    rep.senders = len(names)

    sample_lines = [_scramble_free_line(line, rng) for line in junk]
    for anon in out_blocks:
        sample_lines += [anon.head + anon.lines[0], *anon.lines[1:]]
    sample = "\n".join(sample_lines).rstrip("\n") + "\n"
    _verify(original_of(keep), sample, rep.date_order)

    sample_alone = _outcome(sample, None)
    if sample_alone[0] == "error":
        rep.notes.append(
            f"On its own the sample does not parse ({sample_alone[1]})"
            + (
                ": all its dates are ambiguous, so the reader cannot tell the date order from this slice. "
                "Keep more messages (--max-messages) if you want it to show the order."
                if sample_alone[1] == "DateOrderAmbiguous"
                else "."
            )
        )
    return Anonymized(text=sample, report=rep, had_bom=had_bom)


# ----------------------------------------------------------------------------- command line
def _read_input(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise AnonymizeError(f"Cannot read {path}: {exc.strerror or exc}") from exc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", type=Path, help="a WhatsApp export: .txt, or the .zip an iPhone makes")
    ap.add_argument("-o", "--output", type=Path, required=True, help="where to write the sample (.txt)")
    ap.add_argument(
        "--max-messages", type=int, default=DEFAULT_MAX_MESSAGES,
        help=f"keep only the first N messages (default {DEFAULT_MAX_MESSAGES}; 0 keeps them all)",
    )
    ap.add_argument("--seed", type=int, default=0, help="seed for the random replacement letters (default 0)")
    ap.add_argument("--force", action="store_true", help="overwrite the output file if it exists")
    args = ap.parse_args(argv)

    try:
        if args.max_messages < 0:
            raise AnonymizeError("--max-messages cannot be negative.")
        src, dst = args.input.resolve(), args.output.resolve()
        if src == dst:
            raise AnonymizeError("The output would overwrite your original. Choose another file name.")
        if dst.exists() and not args.force:
            raise AnonymizeError(f"{args.output} already exists. Use --force to replace it.")
        result = anonymize(_read_input(args.input), seed=args.seed, max_messages=args.max_messages)
        args.output.write_text(result.text, encoding="utf-8-sig" if result.had_bom else "utf-8", newline="\n")
    except AnonymizeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error: cannot write {args.output}: {exc.strerror or exc}", file=sys.stderr)
        return 1

    r = result.report
    fmt = f"{r.family}, {r.date_order or 'date order unknown'}, {'12-hour' if r.hour12 else '24-hour'}"
    print(f"Read {fmt}: {r.messages_in_original:,} messages, {r.senders} people.", file=sys.stderr)
    print(
        f"Wrote {r.messages_kept:,} messages and {r.system_blocks_kept} system lines to {args.output}; "
        f"{r.placeholders_kept} WhatsApp placeholders kept as written.",
        file=sys.stderr,
    )
    print("Kept: timestamps, who spoke when, message lengths, punctuation, emoji.", file=sys.stderr)
    print("Changed: every name and every letter or digit in every message.", file=sys.stderr)
    print("Checked: the sample parses to the same structure as the original.", file=sys.stderr)
    for note in r.notes:
        print(f"Note: {note}", file=sys.stderr)
    print("\nThe first lines of the sample (read all of it before you share it):", file=sys.stderr)
    for line in result.text.split("\n")[:6]:
        print(f"  {line}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
