"""The demo couple (docs/STATS.md §6). Every planted fact is checked on the PARSED chat, with the
independent measurements in tools/demo_chat/facts.py and regexes written here, so the generator is
never graded by its own bookkeeping.

  exact     placed on purpose, asserted equal
  budgeted  a quota the generator fills exactly, asserted equal
  banded    comes out of stochastic filler, asserted inside a tolerance band
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from conftest import ROOT
from demo_chat import facts
from demo_chat import params as P
from demo_chat import pools
from demo_chat.build import build, dumps_truth
from lovelm.api import load_chat

DEMO = ROOT / "demo"
ROHAN, TARA = "Rohan", "Tara"


@pytest.fixture(scope="module")
def chat():
    return load_chat((DEMO / "demo_chat.txt").read_bytes())


@pytest.fixture(scope="module")
def msgs(chat):
    return chat.messages


@pytest.fixture(scope="module")
def truth():
    return json.loads((DEMO / "demo_chat.truth.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------------ the files themselves
def test_committed_files_are_a_fresh_deterministic_build():
    demo = build(P.SEED)
    assert demo.text.encode("utf-8") == (DEMO / "demo_chat.txt").read_bytes()
    assert dumps_truth(demo.truth) == (DEMO / "demo_chat.truth.json").read_text(encoding="utf-8")


def test_parser_reads_the_file_exactly_as_generated(chat):
    demo = build(P.SEED)
    assert len(chat.messages) == len(demo.slots)
    for m, s in zip(chat.messages, demo.slots):
        assert (m.ts, m.sender, m.text, m.kind, m.media_type, m.edited) == (
            s.ts, P.NAMES[s.sender], s.text, s.kind, s.media_type, s.edited)


def test_export_quirks_are_present_and_survive_parsing(chat):
    raw = (DEMO / "demo_chat.txt").read_text(encoding="utf-8")
    assert "‎" in raw and " " in raw  # direction marks; narrow no-break space before AM/PM
    meta = chat.meta
    assert (meta.family, meta.date_order, meta.hour12, meta.has_seconds) == ("ios", "DMY", True, True)
    assert chat.warnings == [] and len(chat.system) == 3
    assert sum("\n" in m.text for m in chat.messages) == 23
    assert sum(m.edited for m in chat.messages) == 25
    assert chat.participants == (ROHAN, TARA)


# ------------------------------------------------------------------ exact facts
def test_totals_and_span(msgs):
    assert len(msgs) == 47_382
    assert Counter(m.sender for m in msgs) == {ROHAN: 28_429, TARA: 18_953}
    assert msgs[0].ts == datetime(2024, 1, 3, 21, 14, 8) and msgs[0].text == "hi, is this Tara?"
    assert msgs[0].sender == ROHAN
    assert (msgs[-1].ts.date() - msgs[0].ts.date()).days == 659 and msgs[-1].ts.date() == date(2025, 10, 23)


def test_first_i_love_you_is_taras_on_day_47(msgs):
    ily = re.compile(r"\b(i love you|love you|love u|luv u)\b", re.I)
    first = next(m for m in msgs if ily.search(m.text))
    assert (first.sender, first.ts.date()) == (TARA, date(2024, 2, 19))
    assert (first.ts.date() - msgs[0].ts.date()).days == 47


def test_the_31_message_monologue_and_the_hmm(msgs):
    n, turn, reply = facts.longest_turn(msgs)
    assert n == 31 and turn[0].sender == ROHAN and turn[0].ts == datetime(2024, 6, 14, 1, 12, 3)
    assert reply.sender == TARA and reply.text == "hmm" and reply.ts.date() == date(2024, 6, 14)


def test_the_fight_day_and_the_silence_after_it(msgs):
    days = facts.day_counts(msgs)
    (top, count), = days.most_common(1)
    assert (top, count) == (date(2024, 8, 2), 1204)
    last = [m for m in msgs if facts.chat_day(m.ts) == top][-1]
    assert (last.sender, last.text, last.ts) == (TARA, "ok.", datetime(2024, 8, 2, 23, 48, 22))
    empty = [date(2024, 8, 2) + timedelta(days=i) for i in range(1, 7)]
    assert all(d not in days for d in empty)  # six whole empty days
    assert days[date(2024, 8, 9)] > 0


def test_longest_streak_is_183_days_and_ends_on_the_fight(msgs):
    streaks = facts.active_streaks(msgs, ROHAN, TARA)
    best = max(streaks, key=lambda s: s[2])
    assert best == (date(2024, 2, 2), date(2024, 8, 2), 183)
    others = sorted((s[2] for s in streaks if s != best), reverse=True)
    assert others[0] <= 160  # nothing else comes close (second place is far below 183)
    one_sided = {date(2024, 2, 1), date(2025, 1, 4), date(2025, 6, 14)}  # Tara sends nothing on these days
    tara_days = {facts.chat_day(m.ts) for m in msgs if m.sender == TARA}
    assert not (one_sided & tara_days)


def test_four_silences_and_rohan_broke_every_one(msgs):
    sil = facts.silences(msgs, 48)
    assert len(sil) == 4
    assert all(after.sender == ROHAN for _, after in sil)
    assert sil[0][0].ts.date() == date(2024, 8, 2) and sil[0][1].ts == datetime(2024, 8, 9, 21, 10, 44)


def test_message_10000_is_taras_wait_what_in_may_2024(msgs):
    m = msgs[9999]
    assert (m.sender, m.text) == (TARA, "wait what") and (m.ts.year, m.ts.month) == (2024, 5)


# ------------------------------------------------------------------ budgeted facts
def count(msgs, who, pred):
    return sum(1 for m in msgs if m.sender == who and pred(m))


def test_token_budgets_are_exact(msgs):
    apology = re.compile(r"\b(sorry|sry|my bad|maaf|maafi|i apologi[sz]e|apologies|forgive me)\b", re.I)
    who_is = re.compile(r"\b(who is|who's|who’s|kaun hai|kon hai)\b", re.I)
    babu = re.compile(r"\bbabu\b", re.I)
    text = lambda m: m.kind == "text"
    for who, ok, ap, wi, cry, bb, dele, aud in (
        (ROHAN, 3, 214, 3, 939, 981, 41, 18), (TARA, 38, 9, 27, 1402, 293, 12, 160),
    ):
        assert count(msgs, who, lambda m: text(m) and m.text.strip().lower() in ("ok.", "okay.")) == ok
        assert count(msgs, who, lambda m: text(m) and apology.search(m.text)) == ap
        assert count(msgs, who, lambda m: text(m) and who_is.search(m.text)) == wi
        assert sum(m.text.count("😭") for m in msgs if m.sender == who and text(m)) == cry
        assert sum(len(babu.findall(m.text)) for m in msgs if m.sender == who and text(m)) == bb
        assert count(msgs, who, lambda m: m.kind == "deleted") == dele
        assert count(msgs, who, lambda m: m.media_type == "audio") == aud
    assert sum(m.text.count("😭") for m in msgs if m.kind == "text") == 2341
    emoji = Counter(c for m in msgs if m.kind == "text" for c in re.findall(r"😭|😂|❤️|🥺|🙄|😅|😴|🙈", m.text))
    assert emoji.most_common(1)[0][0] == "😭"  # the top emoji really is 😭


def test_cindy(msgs, truth):
    mentions = [m for m in msgs if re.search(r"\b(cindy|cindyy|sindy|cindi)\b", m.text, re.I)]
    assert len(mentions) == 14
    assert sum(1 for m in mentions if re.search(r"\bcindy\b", m.text, re.I)) == 11
    assert Counter(m.sender for m in mentions) == {TARA: 9, ROHAN: 5}
    orig, reply = mentions[0], mentions[1]
    assert orig.ts == datetime(2025, 3, 14, 23, 42, 17) and orig.sender == ROHAN
    assert orig.text == "cindy from the new team is kinda cute ngl"
    assert (reply.sender, reply.text, (reply.ts - orig.ts).total_seconds()) == (TARA, "who is cindy", 4)
    assert (mentions[-1].ts.date() - orig.ts.date()).days > 200  # she keeps coming up for months
    assert [m.id for m in mentions] == truth["ids"]["cindy_all"]


def test_hinglish_and_semantic_search_sets(msgs, truth):
    khana = [msgs[i].text for i in truth["ids"]["khana"]]
    assert sorted(khana) == sorted(["khana khaya?", "khaana khaya kya", "khana kha liya?", "khaya kya", "khana khaya yaar"])
    paraphrase = [msgs[i].text for i in truth["ids"]["cute_paraphrase"]]
    assert len(paraphrase) == 6 and not any("cute" in t.lower() for t in paraphrase)
    cute = [m for m in msgs if re.search(r"\bcute\b", m.text, re.I)]
    assert [m.id for m in cute] == truth["ids"]["cute_literal_all"]
    assert len(cute) >= 6
    assert sum(1 for m in msgs if m.text.strip().lower().startswith("khana")) >= 3


# ------------------------------------------------------------------ banded facts
def test_reply_times(msgs):
    assert 95 <= (r := facts.median(facts.reply_seconds(msgs, ROHAN))) <= 105, r  # "1m 40s"
    assert 1250 <= (t := facts.median(facts.reply_seconds(msgs, TARA))) <= 1510, t  # "23 min"


def test_who_starts_conversations(msgs):
    init = facts.initiations(msgs)
    assert 0.68 <= init[ROHAN] / sum(init.values()) <= 0.74


def test_double_texts_are_mostly_rohans(msgs):
    d = facts.double_texts(msgs)
    assert d[ROHAN] > 1000 and d[TARA] < 200 and d[ROHAN] > 7 * d[TARA]
    assert 1100 <= d[ROHAN] + d[TARA] <= 1300  # measured 1,190


def test_two_am_is_the_peak_hour(msgs):
    hist = facts.hour_histogram(msgs)
    share = [h / len(msgs) for h in hist]
    ranked = sorted(range(24), key=lambda h: -share[h])
    assert ranked[0] == 2 and share[2] >= 0.085
    assert share[2] - share[ranked[1]] >= 0.015  # a clear winner, not a coin-flip
    assert sum(share[0:5]) >= 0.30  # night share (00:00-04:59)


def test_word_count_and_runtime(msgs):
    words = facts.total_words(msgs)
    assert abs(words - 283_000) <= 1_500
    assert int(words / 36 / 60) == 131  # "131 HRS (OF TYPING)"


def test_profanity_rate_is_pg(msgs):
    low = " ".join(m.text.lower() for m in msgs if m.kind == "text")
    hits = sum(len(re.findall(rf"\b{w}\b", low)) for w in ("damn", "wtf", "crap"))
    assert hits == 310 and 0.5 <= hits / facts.total_words(msgs) * 1000 < 2.0


def test_signature_words_separate_the_two_voices(msgs):
    rohan, tara, _ = facts.signature_words(msgs, ROHAN, TARA)
    assert len({"bro", "scene", "chalo", "sorry", "wait"} & set(rohan)) >= 4, rohan
    assert len({"hmm", "literally", "acha", "lowkey", "nahi"} & set(tara)) >= 4, tara


def test_verdicts_do_not_depend_on_the_conversation_gap(msgs):
    """STATS §6.6: re-cut conversations at 2 h and 6 h; the story must not flip."""
    for hours in (2, 6):
        gap = timedelta(hours=hours)
        init = facts.initiations(msgs, gap)
        assert init[ROHAN] > init[TARA]
        rohan = facts.median(facts.reply_seconds(msgs, ROHAN, gap))
        tara = facts.median(facts.reply_seconds(msgs, TARA, gap))
        assert tara / rohan >= 5, (hours, rohan, tara)
        assert len(facts.silences(msgs, 48)) == 4  # independent of the gap


# ------------------------------------------------------------------ the sidecar
def test_sidecar_points_at_the_right_messages(msgs, truth):
    ids = truth["ids"]
    assert truth["message_count"] == len(msgs)
    assert msgs[ids["first_message"][0]].text == "hi, is this Tara?"
    assert msgs[ids["first_ily"][0]].text == "i love you"
    assert [msgs[i].sender for i in ids["monologue"]] == [ROHAN] * 31
    assert msgs[ids["monologue_reply"][0]].text == "hmm"
    assert msgs[ids["fight_last"][0]].text == "ok."
    assert ids["msg_10000"] == [9999]
    assert len(ids["silence_break"]) == 4
    assert len(ids["multiline"]) == 23 and len(ids["deleted"]) == 53
    for q in truth["queries"]:
        assert q["expect"] and all(0 <= i < len(msgs) for i in q["expect"])


# ------------------------------------------------------------------ pools never leak budgeted words
def _all_pool_strings():
    names = ("FOOD", "PLACE", "WHEN", "THING", "TIME", "MEAL", "SHORT", "MEDIUM", "QUESTIONS", "TOPIC_R",
             "TOPIC_T", "EMOTION", "CONNECT", "PAD", "MULTILINE", "ANSWERS", "OPENERS", "LINK_LEAD")
    for n in names:
        for s in getattr(pools, n):
            yield n, s


@pytest.mark.parametrize("name,text", list(_all_pool_strings()))
def test_generic_pools_contain_no_budgeted_words(name, text):
    low = text.lower()
    for word in pools.RESERVED:
        pattern = rf"\b{re.escape(word)}\b" if re.fullmatch(r"[\w' ’]+", word) else re.escape(word)
        assert not re.search(pattern, low), f"{name}: {text!r} contains reserved {word!r}"
    assert not low.rstrip().endswith("ok.") and low.strip() not in ("ok.", "okay.")
