"""Unit tests for lexicon matching, emoji, quote safety, formatting and edge cases on tiny chats."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from lovelm import copy as C
from lovelm.api import analyze
from lovelm.context import A, B, build_ctx
from lovelm.ingest import normalize_text
from lovelm.parse import parse_chat
from lovelm.stats import REGISTRY, run_all
from lovelm.stats.language import detect_pet_name, rating_letter
from lovelm.text import books, emojis, matcher, phrase_list, squash, stopwords, tokens


def mk(rows, start=datetime(2024, 3, 13, 10, 0)):
    """rows: (minutes_after_start, sender, text) -> a parsed Chat (Android 24h format)."""
    lines = []
    for mins, who, text in rows:
        ts = start + timedelta(minutes=mins)
        lines.append(f"{ts.day:02d}/{ts.month:02d}/{ts.year}, {ts:%H:%M} - {who}: {text}")
    return parse_chat(normalize_text("\n".join(lines) + "\n"))


def ping_pong(n, *, start=0, step=3, texts=("hey", "yo")):
    return [(start + i * step, "Ann" if i % 2 == 0 else "Bo", texts[i % 2]) for i in range(n)]


# ------------------------------------------------------------------ text
def test_squash_collapses_repeats_for_matching_only():
    assert squash("Sorryyy") == "sory" and squash("sorry") == "sory" and squash("It’s") == "it's"
    assert squash("book") == "bok" and squash("a1111") == "a1111"  # digits are not letters


@pytest.mark.parametrize("text", ["SORRYYY!!", "so sorry", "my bad", "Sorry, sorry", "i apologise", "maaf karo"])
def test_apology_matches(text):
    assert matcher("apology").search(squash(text))


@pytest.mark.parametrize("text", ["sorrow", "sorted", "my badge", "apologetic"])
def test_apology_respects_word_boundaries(text):
    assert not matcher("apology").search(squash(text))


def test_prefix_and_emoji_and_short_phrase_boundaries():
    laugh, goodnight, love = matcher("laughter"), matcher("goodnight"), matcher("i_love_you")
    assert laugh.search(squash("hahahahaha")) and laugh.search(squash("lol")) and laugh.search("😂") and not laugh.search(squash("ha"))
    assert goodnight.search(squash("gn babu")) and not goodnight.search(squash("gone home"))
    assert love.search(squash("love u")) and not love.search(squash("love user"))
    assert love.count(squash("love you, love u")) == 2


def test_tokens_ignore_urls_and_keep_apostrophes():
    assert tokens("Don’t open https://x.com/a?b=1 it's a trap") == ["don’t", "open", "it's", "a", "trap"]


@pytest.mark.parametrize("text,n", [("😭😭", 2), ("❤️", 1), ("👨‍👩‍👧", 1), ("👍🏽", 1), ("🇮🇳", 1), ("plain 123 text", 0), ("hi 🙂 there 😂", 2)])
def test_emoji_graphemes(text, n):
    assert len(emojis(text)) == n


def test_lexicon_files_are_sane():
    for name in ("apology", "i_love_you", "affection", "ping", "laughter", "goodnight", "who_is", "profanity", "pet_names"):
        assert phrase_list(name) and all(isinstance(p, str) and p for p in phrase_list(name))
    stop = stopwords()
    assert not {"nahi", "acha", "chalo", "scene", "bro", "hmm", "sorry"} & stop  # distinctive words are never stopwords
    sizes = [b["words"] for b in books()]
    assert sizes == sorted(sizes) and all(b["punch"] and b["unit"] for b in books())


# ------------------------------------------------------------------ quote safety
@pytest.fixture
def quote_ctx():
    rows = ping_pong(30) + [
        (100, "Ann", "meet Priya at nine"), (101, "Bo", "call me on +91 98765 43210"), (102, "Ann", "my pin is 482913"),
        (103, "Bo", "this is one two three four five six seven"), (104, "Ann", "see https://x.com/page"),
        (105, "Bo", "what the hell"), (106, "Ann", "ok see you Bo"), (107, "Bo", "love it"),
    ]
    return build_ctx(mk(rows)), rows


def test_safe_quote_rules(quote_ctx):
    c, rows = quote_ctx
    q = lambda k: c.safe_quote(30 + k)
    assert q(0) is None  # "Priya" is only ever seen capitalised: probably a name
    assert q(1) is None and q(2) is None  # phone number; 4+ digits
    assert q(3) is None  # seven words (max six)
    assert q(4) is None  # a link
    assert q(5) is None  # profanity never goes on a poster
    assert q(6) == "ok see you Bo"  # participants' own names are fine
    assert q(7) == "love it"


def test_proper_noun_heuristic_and_quotes_switch():
    rows = ping_pong(30) + [(100, "Ann", "meet Dave tomorrow"), (101, "Bo", "dave is late again")]
    c = build_ctx(mk(rows))
    assert c.safe_quote(30) == "meet Dave tomorrow"  # 'dave' also appears lowercase: not provably a name
    rows = ping_pong(30) + [(100, "Ann", "meet Dave tomorrow")]
    c = build_ctx(mk(rows))
    assert c.safe_quote(30) is None and "dave" in c.proper_nouns()
    assert build_ctx(mk(ping_pong(30)), quotes=False).safe_quote(0) is None


# ------------------------------------------------------------------ formatting
@pytest.mark.parametrize("sec,coarse,out", [
    (45, False, "45s"), (45, True, "under a minute"), (100, False, "1m 40s"), (100, True, "1 min"), (120, False, "2 min"),
    (1375, False, "23 min"), (3600, False, "1 h"), (7500, False, "2 h 5 min"), (12599, False, "3 h 30 min"),
])
def test_fmt_dur(sec, coarse, out):
    assert C.fmt_dur(sec, coarse) == out


def test_small_formatters():
    assert C.fmt_x(1.5) == "nearly 2×" and C.fmt_x(7.4) == "7×" and C.fmt_date("2024-08-02") == "2 Aug 2024"
    assert [C.tier_of(r) for r in (2.9, 3, 5.99, 6)] == ["mild", "medium", "medium", "extreme"]
    assert C.ordinal_comma(10000) == "10,000th"
    assert [rating_letter(x) for x in (0, 0.49, 0.5, 1.99, 2, 5.99, 6)] == ["G", "G", "PG", "PG", "PG-13", "PG-13", "R"]


# ------------------------------------------------------------------ edge cases on small chats
def test_tiny_chat_does_not_crash_and_skips_what_it_cannot_back_up():
    chat = mk(ping_pong(8))
    r = analyze(chat)
    ids = {s["id"] for s in r["stats"]}
    assert "reply_median" not in ids and "double_texts" not in ids and "signature_words" not in ids
    assert r["archetypes"]["A"]["name"] == "THE LEAD" and r["archetypes"]["B"]["name"] == "THE OTHER LEAD"
    assert r["poster"]["rating"]["text"].startswith("[G]")


def test_a_tie_is_not_a_stat():
    ctx = build_ctx(mk(ping_pong(400, step=1)))
    ids = {s.id for s in run_all(ctx)}
    assert "message_share" not in ids  # exactly 200 each: nothing to say


def test_first_ily_in_the_first_message_is_just_a_greeting():
    rows = [(0, "Ann", "love you"), (1, "Bo", "hi")] + ping_pong(20, start=5)
    ids = {s.id for s in run_all(build_ctx(mk(rows)))}
    assert "first_ily" not in ids
    rows = ping_pong(20) + [(60, "Bo", "i love you")]
    assert "first_ily" in {s.id for s in run_all(build_ctx(mk(rows)))}


def test_silence_is_counted_in_whole_empty_days():
    rows = ping_pong(10) + [(60 * 24 * 4 + 120 + i, "Bo", "back") for i in range(3)]  # 13 Mar .. 17 Mar
    s = {x.id: x for x in run_all(build_ctx(mk(rows)))}["longest_silence"]
    assert s.values["d"] == 3 and s.values["W"] == "Bo"  # 14th, 15th and 16th had no messages


def test_pet_name_falls_back_to_the_list_when_nothing_follows_a_greeting():
    rows = ping_pong(10) + [(100 + i, "Ann" if i % 2 else "Bo", "so tired baby") for i in range(30)]
    token, n, _ = detect_pet_name(build_ctx(mk(rows)))
    assert token == "baby" and n == 30


def test_apology_counts_one_per_message_and_survives_stretched_spelling():
    rows = ping_pong(300, step=2) + [(700 + i, "Bo", "sooorrryyy sorry") for i in range(25)]
    ctx = build_ctx(mk(rows), spicy=True)
    s = {x.id: x for x in run_all(ctx)}["apologies"]
    assert (s.values["a"], s.values["b"]) == (0, 25)


# ------------------------------------------------------------------ copy
def test_template_conditionals_and_unfillable_templates_are_skipped_quietly():
    from lovelm.stats.base import Stat
    ctx = build_ctx(mk(ping_pong(30)))
    st = Stat("first_ily", "P0", "event", "milestone", "F", False, "", 1.0, "B", 0.9,
              {"n": 5, "W": "Bo", "L": "Ann", "win": "B", "dur": None, "plot_twist": False, "date": "2024-03-13"}, [])
    lines = C.render_stat(st, ctx)
    assert "It took 5 days for someone to say 'I love you'. It was Bo." in lines
    assert not any("Plot twist" in x or "replied in" in x for x in lines)
    st.values["plot_twist"] = True
    assert any("Plot twist" in x for x in C.render_stat(st, ctx))


def test_braces_in_a_name_are_data_not_templates():
    ctx = build_ctx(mk(ping_pong(30)), names={"A": "{n}", "B": "{evil}"})
    from lovelm.stats.base import Stat
    st = Stat("longest_monologue", "P0", "event", "effort", "N", False, "", 1.0, "A", 1.0,
              {"n": 9, "W": "{n}", "L": "{evil}", "win": "A"}, [])
    assert C.render_stat(st, ctx) == ["{n} once sent 9 messages in a row. Nobody interrupted. Nobody could."]


def test_every_stat_has_copy_and_every_bank_entry_has_a_stat():
    ids = {s.id for s in REGISTRY}
    assert ids == set(C.BANK), (ids ^ set(C.BANK))
    assert len(ids) >= 45


def test_all_banked_templates_stay_short_enough_to_be_a_poster_line():
    long = [(k, t) for k, v in C.BANK.items() for t in (sum(v.values(), []) if isinstance(v, dict) else v) if len(t) > 120]
    assert not long, long
