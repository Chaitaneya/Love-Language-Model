"""Golden tests: every stat against the facts planted in the demo couple (docs/STATS.md §6.3), plus
cross-checks against the independent measurements in tools/demo_chat/facts.py."""

from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from conftest import ROOT
from demo_chat import facts
from lovelm import config
from lovelm.api import analyze, load_chat
from lovelm.context import A, B, build_ctx

DEMO = ROOT / "demo" / "demo_chat.txt"


@pytest.fixture(scope="module")
def chat():
    return load_chat(DEMO.read_bytes())


@pytest.fixture(scope="module")
def plain(chat):
    return analyze(chat, seed=1234)


@pytest.fixture(scope="module")
def spicy(chat):
    return analyze(chat, seed=1234, spicy=True)


def stat(result, sid):
    found = [s for s in result["stats"] if s["id"] == sid]
    assert found, f"stat {sid} missing"
    return found[0]


def vals(result, sid):
    return stat(result, sid)["values"]


# ------------------------------------------------------------------ shape
def test_result_is_plain_json_with_the_documented_keys(plain):
    json.dumps(plain)
    assert set(plain) == {"schema", "meta", "people", "stats", "poster", "meters", "archetypes", "words", "charts", "seed"}
    assert plain["schema"] == 1 and plain["people"] == {"A": {"name": "Rohan"}, "B": {"name": "Tara"}}
    assert plain["meta"]["messages"] == 47_382 and plain["meta"]["range"] == ["2024-01-03", "2025-10-23"]
    assert all(s["lines"] for s in plain["stats"] if s["id"] != "heartbeat")  # every shown stat has a line


def test_spicy_stats_are_hidden_unless_asked_for(plain, spicy):
    spicy_only = {"apologies", "clingy_pings", "triple_texts", "silence_breaker", "bang_then_silence", "who_is_that"}
    assert not spicy_only & {s["id"] for s in plain["stats"]}
    assert spicy_only <= {s["id"] for s in spicy["stats"]}
    assert "clingy" not in plain["meters"] and "clingy" in spicy["meters"]


# ------------------------------------------------------------------ P0 stats against planted facts
def test_volume(plain):
    assert vals(plain, "messages_total")["n"] == 47_382
    assert vals(plain, "span_days")["n"] == 659
    assert vals(plain, "runtime_typing")["hours"] == 131
    assert vals(plain, "msgs_per_day")["n"] == 72
    assert vals(plain, "words_total_books")["words"] == 283_000
    share = vals(plain, "message_share")
    assert (share["a"], share["b"], share["W"], share["pct"]) == (28_429, 18_953, "Rohan", 60)


def test_rhythm(plain):
    peak = vals(plain, "peak_hour")
    assert peak["hour"] == 2 and peak["hour_label"] == "2 AM" and peak["night"] and peak["share"] >= 0.085
    assert vals(plain, "night_owl_share")["pct"] >= 30


def test_longest_streak(plain):
    assert vals(plain, "longest_streak") == {"n": 183, "start": "2024-02-02", "end": "2024-08-02"}


def test_initiator_and_replies(plain):
    ini = vals(plain, "initiator")
    assert ini["W"] == "Rohan" and 68 <= ini["pct"] <= 74 and ini["k"] == 7
    rep = stat(plain, "reply_median")
    v = rep["values"]
    assert (v["slow"], v["fast"], rep["subject"]) == ("Tara", "Rohan", "B")
    assert v["sec_fast"] == 100 and 1250 <= v["sec_slow"] <= 1510 and v["r"] >= 5
    assert "Rohan replies in 1m 40s. Tara replies in 23 min. Tara is 'busy.'" in rep["lines"]


def test_longest_monologue(plain):
    v = vals(plain, "longest_monologue")
    assert (v["n"], v["W"], v["q"], v["date"]) == (31, "Rohan", "hmm", "2024-06-14")
    assert "Rohan once sent 31 messages in a row. Tara replied 'hmm'." in stat(plain, "longest_monologue")["lines"]


def test_longest_monologue_lengths_are_the_real_messages(chat, plain):
    # the poster draws one bar per message at this length, so it must be the actual run, in order
    v = vals(plain, "longest_monologue")
    run = chat.messages[v["start_id"]: v["end_id"] + 1]
    assert len(v["lens"]) == v["n"] == len(run) == 31
    assert {m.sender for m in run} == {"Rohan"}
    assert v["lens"] == [len(m.text) if m.kind == "text" else 0 for m in run]
    assert chat.messages[v["reply_id"]].sender == "Tara" and chat.messages[v["reply_id"]].text == "hmm"


def test_first_i_love_you_and_first_message(plain):
    ily = vals(plain, "first_ily")
    assert (ily["n"], ily["W"], ily["date"], ily["plot_twist"]) == (47, "Tara", "2024-02-19", True)
    assert "It took 47 days for someone to say 'I love you'. It was Tara. Plot twist." in stat(plain, "first_ily")["lines"]
    first = vals(plain, "first_message")
    assert (first["W"], first["q"], first["date"]) == ("Rohan", "hi, is this Tara?", "2024-01-03")


def test_signature_words(plain):
    v = vals(plain, "signature_words")
    assert len({"bro", "scene", "chalo", "sorry", "wait"} & set(v["a"])) >= 4, v["a"]
    assert len({"hmm", "literally", "acha", "lowkey", "nahi"} & set(v["b"])) >= 4, v["b"]
    assert "😭" not in v["a"] + v["b"]  # emoji belong in the cloud, not in "signature words"


def test_emoji_and_pet_name(plain):
    e = vals(plain, "emoji_top")
    assert (e["emoji"], e["n"], e["a"], e["b"]) == ("😭", 2341, 939, 1402)
    p = vals(plain, "pet_name")
    assert (p["token"], p["n"], p["a"], p["b"]) == ("babu", 1274, 981, 293)


# ------------------------------------------------------------------ P1 and the rest
def test_counts_and_ratios(plain, spicy):
    d = vals(plain, "double_texts")
    assert (d["W"], d["a"], d["b"]) == ("Rohan", 1067, 123)
    o = vals(plain, "ok_period")
    assert (o["a"], o["b"], o["n"], o["W"]) == (3, 38, 38, "Tara")
    assert (vals(plain, "deleted")["a"], vals(plain, "deleted")["b"]) == (41, 12)
    assert (vals(plain, "voice_notes")["a"], vals(plain, "voice_notes")["b"]) == (18, 160)
    assert (vals(spicy, "apologies")["a"], vals(spicy, "apologies")["b"]) == (214, 9)
    assert (vals(spicy, "who_is_that")["a"], vals(spicy, "who_is_that")["b"]) == (3, 27)
    s = vals(plain, "swearing")
    assert (s["n"], s["letter"]) == (310, "PG") and 1.0 < s["rate"] < 1.2


def test_events(plain, spicy):
    assert vals(plain, "busiest_day")["n"] == 1204 and vals(plain, "busiest_day")["date"] == "2024-08-02"
    sil = vals(plain, "longest_silence")
    assert (sil["d"], sil["W"], sil["start"], sil["end"]) == (6, "Rohan", "2024-08-02", "2024-08-09")
    bang = vals(spicy, "bang_then_silence")
    assert (bang["date"], bang["n"], bang["d"]) == ("2024-08-02", 1204, 6)
    sb = vals(spicy, "silence_breaker")
    assert (sb["k"], sb["n"], sb["W"], sb["all"]) == (4, 4, "Rohan", True)
    assert "Rohan broke every silence over 2 days. 4 out of 4." in stat(spicy, "silence_breaker")["lines"]
    assert vals(spicy, "fight_days")["n"] == 1


def test_message_milestone_points_at_a_real_message(chat, plain):
    m = vals(plain, "message_milestones")
    msg = chat.messages[m["n"] - 1]
    assert m["id"] == m["n"] - 1 and m["W"] == msg.sender and m["q"] == msg.text and m["date"] == msg.ts.date().isoformat()
    assert chat.messages[9999].text == "wait what" and chat.messages[9999].sender == "Tara"  # the planted one


def test_makes_laugh_and_affection_have_sensible_winners(plain):
    assert vals(plain, "affection_count")["W"] == "Rohan"  # the demo's hopeless romantic
    assert vals(plain, "makes_laugh")["W"] == "Tara"


# ------------------------------------------------------------------ agreement with the independent checker
def test_stats_agree_with_the_independent_measurements(chat, plain):
    msgs = chat.messages
    f = facts
    init = f.initiations(msgs)
    assert (vals(plain, "initiator")["a"], vals(plain, "initiator")["b"]) == (init["Rohan"], init["Tara"])
    dbl = f.double_texts(msgs)
    assert (vals(plain, "double_texts")["a"], vals(plain, "double_texts")["b"]) == (dbl["Rohan"], dbl["Tara"])
    r = vals(plain, "reply_median")
    assert r["sec_a"] == round(f.median(f.reply_seconds(msgs, "Rohan"))) and r["sec_b"] == round(f.median(f.reply_seconds(msgs, "Tara")))
    streak = max(f.active_streaks(msgs, "Rohan", "Tara"), key=lambda s: s[2])
    assert (vals(plain, "longest_streak")["n"], vals(plain, "longest_streak")["start"]) == (streak[2], streak[0].isoformat())
    assert vals(plain, "peak_hour")["hour"] == max(range(24), key=f.hour_histogram(msgs).__getitem__)
    rohan, tara, _ = f.signature_words(msgs, "Rohan", "Tara")
    assert set(vals(plain, "signature_words")["a"][:3]) <= set(rohan[:5] + ["babu"])


# ------------------------------------------------------------------ meters and archetypes
def test_love_meter(plain, spicy):
    m = plain["meters"]["love"]
    assert abs(m["A"] + m["B"] - 100) < 0.2 and m["lead"] == "A" and m["subtitle"] == "text effort"
    assert abs(sum(c["weight"] for c in m["components"]) - 1) < 0.01
    assert "loves" not in m["verdict"].lower() and "%" not in m["verdict"]
    k = spicy["meters"]["clingy"]
    assert k["lead"] == "A" and k["labels"]["A"] == "Level: Notification Enthusiast"


def test_archetypes(plain, spicy):
    assert (plain["archetypes"]["A"]["name"], plain["archetypes"]["B"]["name"]) == ("THE DOUBLE TEXTER", "THE GHOST")
    assert plain["archetypes"]["A"]["key"] != plain["archetypes"]["B"]["key"]
    assert spicy["archetypes"]["A"]["key"] != spicy["archetypes"]["B"]["key"]


# ------------------------------------------------------------------ the poster
def test_poster_matches_the_documented_example(plain):
    p = plain["poster"]
    assert p["title"]["text"] == "2 AM AND STILL TYPING"
    assert p["laurel"]["text"] == "WINNER · LONGEST STREAK · 183 DAYS"
    assert p["top_critic"]["stat"] == "first_ily" and p["top_critic"]["stars"] == 5 and "Plot twist" in p["top_critic"]["line"]
    assert [c["stat"] for c in p["critics"]] == ["longest_monologue", "reply_median"]
    assert [(b["name"], b["archetype"]) for b in p["billing"]] == [("ROHAN", "THE DOUBLE TEXTER"), ("TARA", "THE GHOST")]
    assert p["release"] == "IN CHATS SINCE 3 JAN 2024" and p["runtime"] == "131 HRS (OF TYPING)"
    assert p["rating"]["text"] == '[PG] for 2,341 😭, excessive use of "babu" and 38 passive-aggressive "ok."s'
    assert p["tagline"] in {
        "47,382 messages. 659 days. Zero chill.", "659 days. 47,382 messages. One of you is typing.",
        "Based on 283,000 words and a series of poor decisions.", "72 messages a day. No notes.", "A love story in 47,382 parts."}
    assert p["fine_print"][1] == "No chats were stored in the making of this poster."
    assert len(p["heartbeat"]) == 22 and sum(p["heartbeat"]) == 47_382  # Jan 2024 .. Oct 2025


def test_spicy_poster(spicy):
    p = spicy["poster"]
    assert p["title"]["text"] == "SORRY 214"
    assert p["rating"]["letter"] == "PG-13" and p["rating"]["reasons"][-1] == "mild emotional damage"
    assert "214 apologies" in p["rating"]["text"]


@pytest.mark.parametrize("fixture", ["plain", "spicy"])
def test_the_fairness_rule(fixture, request):
    r = request.getfixturevalue(fixture)
    p = r["poster"]
    limit = 2 if fixture == "spicy" else 1
    lines = [c for c in p["critics"]]
    used = {s["id"]: s for s in r["stats"]}
    for side in ("A", "B"):
        ids = [c["stat"] for c in lines] + [p["laurel"]["stat"]]
        unflattering = [i for i in ids if used[i]["valence"] == "U" and used[i]["subject"] == side]
        assert len(unflattering) <= limit
    assert used[p["top_critic"]["stat"]]["valence"] in ("F", "N")  # something kind always comes first
    themes = [used[c["stat"]]["theme"] for c in lines]
    assert len(set(themes)) == len(themes)  # one line per theme
    assert all(len(c["line"]) <= 90 for c in lines + [p["top_critic"]])


def test_quotes_are_real_messages_and_can_be_switched_off(chat, plain):
    quoted = 0
    for s in plain["stats"]:
        if "q" in s["values"]:  # a quoted line: the quote must be a verbatim message from the chat
            assert any(chat.messages[i].text.strip() == s["values"]["q"] for i in s["quote_ids"])
            quoted += 1
        assert all(0 <= i < len(chat.messages) for i in s["quote_ids"])  # ids can also just point at a moment
    assert quoted >= 3
    off = analyze(chat, seed=1234, quotes=False)
    assert not any("q" in s["values"] for s in off["stats"])
    mono = stat(off, "longest_monologue")["lines"]
    assert mono == ["Rohan once sent 31 messages in a row. Nobody interrupted. Nobody could."]


def test_reroll_is_reproducible_and_actually_changes_the_poster(chat, plain):
    again = analyze(chat, seed=1234)
    assert json.dumps(again, sort_keys=True) == json.dumps(plain, sort_keys=True)
    posters = {json.dumps(analyze(chat, seed=s)["poster"], sort_keys=True) for s in range(1, 7)}
    assert len(posters) >= 3
    assert analyze(chat, seed=9)["stats"] == analyze(chat, seed=9)["stats"]


def test_names_and_swap_are_cosmetic(chat, plain):
    nick = analyze(chat, names={"A": "Ro", "B": "T"})
    assert nick["people"]["A"]["name"] == "Ro" and "Ro once sent 31 messages" in json.dumps(nick["poster"])
    swapped = analyze(chat, swap=True)
    assert swapped["people"]["A"]["name"] == "Tara"
    assert vals(swapped, "reply_median")["sec_fast"] == 100 and vals(swapped, "reply_median")["slow"] == "Tara"
    assert swapped["poster"]["title"]["text"] == plain["poster"]["title"]["text"]


# ------------------------------------------------------------------ STATS §6.6: verdicts must not depend on our constants
@pytest.mark.parametrize("hours", [2, 6])
def test_verdicts_survive_a_different_conversation_gap(chat, hours):
    r = analyze(chat, spicy=True, conv_gap_hours=hours)
    assert vals(r, "initiator")["W"] == "Rohan"
    rep = vals(r, "reply_median")
    assert rep["slow"] == "Tara" and rep["r"] >= 5
    assert vals(r, "peak_hour")["hour"] == 2 and vals(r, "longest_streak")["n"] == 183
    sb = vals(r, "silence_breaker")
    assert (sb["k"], sb["n"]) == (4, 4)
    assert [r["archetypes"][s]["name"] for s in "AB"] == ["THE DOUBLE TEXTER", "THE GHOST"]


def test_cloud_surfaces_the_seed_words(plain):
    cloud = plain["words"]
    a = {w["w"] for w in cloud["dueling"]["A"][:10]}
    b = {w["w"] for w in cloud["dueling"]["B"][:10]}
    assert {"bro", "scene", "chalo"} <= a and {"hmm", "nahi", "acha", "literally"} <= b
    assert all(w["z"] > 0 for w in cloud["dueling"]["A"]) and all(w["z"] < 0 for w in cloud["dueling"]["B"])
    assert cloud["shared"] and cloud["tokens"]["A"] > cloud["tokens"]["B"]


def test_charts(plain):
    ch = plain["charts"]
    assert sum(ch["heatmap"]["cells"][d][h] for d in range(7) for h in range(24)) == 47_382
    assert ch["heartbeat"]["months"][0] == "2024-01" and ch["heartbeat"]["months"][-1] == "2025-10"
    assert sum(ch["reply_hist"]["A"]) > 5000 and len(ch["reply_hist"]["labels"]) == len(ch["reply_hist"]["A"])


def test_analysis_is_fast_enough(chat):
    import time
    t = time.time()
    analyze(chat, spicy=True)
    assert time.time() - t < 6, "STATS budget: well under the 5 s in the PRD (this is CPython; Pyodide is slower)"


def test_output_does_not_depend_on_hash_randomization():
    """Regression: word-cloud ties were ordered by Python set iteration, which changes with PYTHONHASHSEED,
    so two processes (or CPython vs Pyodide) disagreed. Same seed must mean the same bytes everywhere."""
    import hashlib
    import os
    import subprocess
    import sys
    code = (
        "import sys, json, hashlib\n"
        f"sys.path.insert(0, {str(ROOT / 'core')!r})\n"
        "from lovelm.api import load_chat, analyze\n"
        f"r = analyze(load_chat(open({str(DEMO)!r}, 'rb').read()), seed=7, spicy=True)\n"
        "print(hashlib.sha256(json.dumps(r, sort_keys=True, ensure_ascii=False).encode()).hexdigest())\n"
    )
    digests = {
        subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, check=True,
                       env={**os.environ, "PYTHONHASHSEED": str(seed)}).stdout.strip()
        for seed in (1, 2, 3)
    }
    assert len(digests) == 1, digests
