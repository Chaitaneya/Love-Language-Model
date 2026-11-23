"""The scripted parts of the demo chat: every planted event of docs/STATS.md §6.3 and §6.5.

Scene messages are `protected`: later stages never edit, remove or reorder them. Times are written
as "HH:MM:SS" on a calendar day; an hour of 24 or more means after midnight (24:12:30 = 00:12:30 next day)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from . import params as P
from .model import Conv, Schedule, Slot
from .rng import Rng

R, T = P.R, P.T


def at(day: date, hhmmss: str) -> datetime:
    h, m, s = (int(x) for x in hhmmss.split(":"))
    return datetime.combine(day, time(0)) + timedelta(hours=h, minutes=m, seconds=s)


def scene(day: date, items: list[tuple]) -> Conv:
    """items: (time, sender, text) or (time, sender, text, [tags])."""
    slots = []
    for it in items:
        when, sender, text = it[0], it[1], it[2]
        tags = list(it[3]) if len(it) > 3 else []
        slots.append(Slot(at(day, when), sender, text, protected=True, role="scene", tags=tags))
    for a, b in zip(slots, slots[1:]):
        assert a.ts < b.ts, f"scene times must increase: {a.ts} {b.ts}"
        assert b.ts - a.ts < P.CONV_GAP, f"gap inside a scene reaches the conversation threshold: {a.ts}"
    return Conv(slots, scene=True)


@dataclass
class Scenes:
    convs: list[Conv] = field(default_factory=list)
    forbidden: list[tuple[datetime, datetime]] = field(default_factory=list)
    tara_zero_days: set[date] = field(default_factory=set)
    skip_days: set[date] = field(default_factory=set)  # chat days with no streak requirement
    system: list[tuple[datetime, str]] = field(default_factory=list)


def _silence(sc: Scenes, start: datetime, end: datetime) -> None:
    """No message may fall in [start, end). A window of 48 h or more is a planted silence."""
    sc.forbidden.append((start, end))
    d = (start - P.DAY_CUT).date()
    while (datetime.combine(d, time(0)) + P.DAY_CUT) < end:
        day_start = datetime.combine(d, time(0)) + P.DAY_CUT
        if day_start >= start and day_start + timedelta(hours=24) <= end:
            sc.skip_days.add(d)
        d += timedelta(days=1)


# ---------------------------------------------------------------- the fight (2 Aug 2024)
_FIGHT_R = [
    "i didn't mean it like that", "why are you twisting everything", "you're not even listening",
    "pick up the call", "please talk to me", "just say something", "i'm right here",
    "can we talk properly", "i was wrong about the tone", "i overreacted", "this is exhausting",
    "you always shut down", "i'm not the villain here", "answer me", "this silence is worse than the fight",
    "fine be like that", "text me when you're ready", "are you there", "hello??", "??",
    "i can't do this over text", "just call me", "five minutes that's all", "i'll come over",
    "tell me what to fix", "i hate this", "you could at least reply", "i'm begging here",
    "okay i get it", "i'm not leaving", "talk to me", "i'll wait here", "please",
    "i'm outside your building", "come down for two minutes", "i brought your favourite",
    "you can ignore me but i'm still here", "i just want to fix this", "what did i do",
]
_FIGHT_R_SORRY = [
    "sorry", "i'm sorry", "sorry okay", "sorry sorry sorry", "i'm so sorry", "sorry i messed up",
    "sorry i shouldn't have said that", "really sorry", "sorry for today", "sorry for everything",
]
_FIGHT_T = (
    ["hmm"] * 9 + ["ok"] * 5 + ["no"] * 3 + ["stop"] * 3
    + ["leave it", "i said leave it", "i'm not angry", "i'm just tired", "you don't get it",
       "it's always about how you feel", "not now", "i need space", "don't call",
       "i'll text you later", "you always do this", "this isn't about the message",
       "i literally said i need time", "lowkey exhausted", "acha fine", "nahi", "just go",
       "please stop texting", "i can't right now", "you're not listening either", "it's fine",
       "whatever", "i said it's fine", "go to sleep", "we'll talk tomorrow", "i can't deal with this",
       "can you stop", "you're making it worse", "😭", "this is so stupid 😭", "i hate fighting 😭"]
)


def _fight(rng: Rng) -> Conv:
    day = P.FIGHT_DAY
    phases = [("07:12:00", "10:30:00", 260, R), ("11:40:00", "15:40:00", 330, T), ("18:30:00", "23:48:22", 614, R)]
    senders: list[str] = []
    times: list[datetime] = []
    for p_idx, (a, b, n, first) in enumerate(phases):
        seq: list[str] = []
        who = first
        while len(seq) < n:
            mean, cap = (4.0, 14) if who == R else (2.2, 7)
            k = min(1 + int(-__import__("math").log(max(rng.random(), 1e-12)) * (mean - 1)), cap)
            seq.extend([who] * min(k, n - len(seq)))
            who = P.OTHER[who]
        raw = []
        for i in range(1, n):
            if seq[i] != seq[i - 1]:
                raw.append(min(rng.lognorm(40 if seq[i] == T else 22, 0.8), 240))
            else:
                raw.append(min(rng.lognorm(6, 0.7), 120))
        span = (at(day, b) - at(day, a)).total_seconds()
        f = span / sum(raw)
        t = at(day, a)
        senders.append(seq[0]); times.append(t)
        acc = 0.0
        for i, d in enumerate(raw, start=1):
            acc += d * f
            senders.append(seq[i]); times.append(at(day, a) + timedelta(seconds=round(acc)))
    # the last two messages: Rohan pleads, Tara closes the day with "ok."
    senders[-2], senders[-1] = R, T
    for i in range(1, len(times)):  # rounding must never make two messages share a second
        if times[i] <= times[i - 1]:
            times[i] = times[i - 1] + timedelta(seconds=1)
    assert len(senders) == P.FIGHT_MESSAGES == 1204

    rohan_idx = [i for i, s in enumerate(senders[:-2]) if s == R]
    sorry_at = set(rng.sample(rohan_idx, 62))
    texts = []
    for i, s in enumerate(senders):
        if i == len(senders) - 1:
            texts.append("ok.")
        elif i == len(senders) - 2:
            texts.append("can we please just sleep on it and talk tomorrow")
        elif s == R:
            texts.append(rng.choice(_FIGHT_R_SORRY) if i in sorry_at else rng.choice(_FIGHT_R))
        else:
            texts.append(rng.choice(_FIGHT_T))
    slots = [Slot(t, s, x, protected=True, role="scene") for t, s, x in zip(times, senders, texts)]
    slots[-1].tags.append("fight_last")
    slots[0].tags.append("fight_first")
    for a, b in zip(slots, slots[1:]):
        assert b.ts - a.ts < P.CONV_GAP
    return Conv(slots, scene=True)


# ---------------------------------------------------------------- Rohan-only days (Tara sends nothing)
def _tara_zero_day(sc: Scenes, day: date, plan: list[tuple[str, list[str]]]) -> None:
    sc.tara_zero_days.add(day)
    for start, lines in plan:
        t = at(day, start)
        items = []
        for i, line in enumerate(lines):
            items.append((_hms(t - datetime.combine(day, time(0))), R, line))
            t += timedelta(seconds=40 + 23 * i)  # always well under 10 minutes
        sc.convs.append(scene(day, items))


def _hms(delta: timedelta) -> str:
    s = int(delta.total_seconds())
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


# ---------------------------------------------------------------- everything
def build_scenes(rng: Rng) -> Scenes:
    sc = Scenes()

    # 1. the very first conversation (3 Jan 2024): nothing exists before it
    sc.forbidden.append((datetime(2024, 1, 3), at(date(2024, 1, 3), "21:14:08")))
    sc.convs.append(scene(date(2024, 1, 3), [
        ("21:14:08", R, "hi, is this Tara?", ["first_message"]),
        ("21:15:10", T, "yeah, this is tara. you are?"),
        ("21:15:45", R, "Priya gave me your number"),
        ("21:15:49", R, "i'm Rohan, her cousin"),
        ("21:18:59", T, "ohh the one from pune?"),
        ("21:19:40", R, "yes that one"),
        ("21:19:42", R, "she said you know a good place for biryani"),
        ("21:23:42", T, "i do"),
        ("21:24:02", T, "but i'm not telling a stranger"),
        ("21:24:57", R, "fair enough"),
        ("21:25:06", R, "what if i guess your favourite"),
        ("21:30:16", T, "go on"),
        ("21:30:38", R, "chicken dum"),
        ("21:37:18", T, "...fine you're half right"),
    ]))

    # 2. the first "I love you": Tara, 19 Feb 2024, day 47
    sc.convs.append(scene(date(2024, 2, 19), [
        ("22:51:20", R, "you up?"), ("22:52:55", T, "barely"), ("22:53:25", R, "i can't sleep"),
        ("22:53:29", R, "my head is full of random stuff"), ("22:56:49", T, "same"),
        ("22:57:39", R, "what are you thinking about"), ("23:04:39", T, "you"), ("23:04:42", T, "obviously"),
        ("23:05:27", R, "obviously??"), ("23:05:30", R, "explain"),
        ("23:15:40", T, "i don't know how to say this without sounding dumb"), ("23:16:08", R, "say it dumb"),
        ("23:31:08", T, "i love you", ["first_ily"]), ("23:32:08", R, "wait"), ("23:32:10", R, "say that again"),
        ("23:32:45", R, "please"), ("23:36:45", T, "i love you. don't make it weird"),
        ("23:37:25", R, "i love you too"), ("23:37:31", R, "i've wanted to say it for two weeks"),
        ("23:42:31", T, "then you're slower than me"), ("23:42:52", R, "i'll live with it"),
        ("23:45:52", T, "goodnight rohan"), ("23:46:17", R, "goodnight tara"),
    ]))

    # 3. the monologue (14 Jun 2024): 31 messages from Rohan, then Tara says "hmm"
    speech = [
        "ok so listen", "i've been thinking about this for like a week",
        "you said yesterday that i never ask about your day", "and you're right", "i ask the usual stuff",
        "did you eat, how was work, did you reach", "that's not really asking", "that's just checking attendance",
        "so here's what i'm going to do differently", "one: i'll ask one real question every day",
        "not what did you eat", "something like what was the best part of your day",
        "two: i'll stop sending 40 reels at 1am", "okay maybe 20",
        "three: i will try to not take it personally when you reply late", "i know you're busy",
        "i know your manager is a nightmare", "i know you're not ignoring me", "but my brain does the thing anyway",
        "it goes quiet and then i start making up stories", "like you're angry or bored or found someone better",
        "which is dumb because i know you", "and you've never given me a reason",
        "i just get anxious when it's quiet", "that's a me problem not a you problem", "but i thought you should know",
        "so that you don't think i'm being weird when i text twice", "which i will probably still do",
        "anyway", "that's it", "that's the whole speech",
    ]
    assert len(speech) == 31
    d = date(2024, 6, 14)
    t = at(d, "01:12:03")
    items: list[tuple] = [
        ("00:41:13", T, "i'm so tired"), ("00:44:02", R, "then sleep na"), ("00:51:30", T, "can't. work stuff"),
        ("00:52:10", R, "tell me?"), ("01:05:44", T, "later"),
    ]
    for i, line in enumerate(speech):
        items.append((_hms(t - datetime.combine(d, time(0))), R, line, ["monologue"] + (["monologue_first"] if i == 0 else [])))
        t += timedelta(seconds=rng.randint(38, 110))
    last = t - timedelta(seconds=0)
    items[-1] = items[-1][:3] + (items[-1][3] + ["monologue_last"],)
    t = last + timedelta(seconds=1210)
    items.append((_hms(t - datetime.combine(d, time(0))), T, "hmm", ["monologue_reply"]))
    t += timedelta(seconds=50)
    items.append((_hms(t - datetime.combine(d, time(0))), R, "that's it? just hmm?"))
    t += timedelta(seconds=1200)
    items.append((_hms(t - datetime.combine(d, time(0))), T, "i'm sleeping. night"))
    t += timedelta(seconds=40)
    items.append((_hms(t - datetime.combine(d, time(0))), R, "night babu"))
    sc.convs.append(scene(d, items))

    # 4. the fight (2 Aug 2024) and the six silent days after it
    sc.forbidden.append((at(P.FIGHT_DAY, "00:00:00"), at(P.FIGHT_DAY, "07:12:00")))
    sc.convs.append(_fight(rng.fork("fight")))
    _silence(sc, at(date(2024, 8, 3), "00:00:00"), at(date(2024, 8, 9), "21:10:44"))
    sc.convs.append(scene(date(2024, 8, 9), [
        ("21:10:44", R, "hey", ["silence_break", "silence_break_1"]), ("21:48:03", T, "hey"), ("21:48:40", R, "can we talk"),
        ("21:52:10", T, "ya"), ("21:52:55", R, "i hate this"), ("21:55:30", T, "i know"),
        ("21:56:00", R, "i'm here whenever"), ("22:10:20", T, "tomorrow. i'll call you"), ("22:10:50", R, "okay"),
        ("22:11:10", R, "goodnight tara"),
    ]))

    # 5. three more silences of at least 48 h, every one ended by Rohan
    _silence(sc, at(date(2024, 10, 12), "00:00:00"), at(date(2024, 10, 14), "11:05:21"))
    sc.convs.append(scene(date(2024, 10, 14), [
        ("11:05:21", R, "hey babu", ["silence_break", "silence_break_2"]), ("11:40:10", T, "hey"), ("11:41:00", R, "you okay?"),
        ("11:58:30", T, "yeah just needed a couple days"), ("11:59:10", R, "okay"), ("11:59:40", R, "i miss you"),
        ("12:20:05", T, "i know"),
    ]))
    _silence(sc, at(date(2025, 2, 8), "00:00:00"), at(date(2025, 2, 10), "09:40:17"))
    sc.convs.append(scene(date(2025, 2, 10), [
        ("09:40:17", R, "hey", ["silence_break", "silence_break_3"]), ("10:20:44", T, "hi"), ("10:21:30", R, "so..."),
        ("10:40:10", T, "i'm not mad. i just wanted quiet"), ("10:40:50", R, "quiet for two days?"),
        ("11:15:00", T, "yes rohan"), ("11:15:30", R, "okay noted"),
    ]))
    _silence(sc, at(date(2025, 7, 19), "00:00:00"), at(date(2025, 7, 21), "10:15:09"))
    sc.convs.append(scene(date(2025, 7, 21), [
        ("10:15:09", R, "hey", ["silence_break", "silence_break_4"]), ("11:02:33", T, "hey"), ("11:03:10", R, "long weekend"),
        ("11:30:00", T, "yeah i switched off for a bit"), ("11:30:40", R, "next time tell me first"),
        ("12:05:12", T, "okay fair"),
    ]))

    # 6. days on which Tara sends nothing: only Rohan, pinging
    _tara_zero_day(sc, date(2024, 2, 1), [
        ("09:05:12", ["good morning", "you there?", "hello?"]),
        ("15:40:31", ["did you eat", "??", "reply when you see this"]),
        ("22:10:55", ["hey", "everything okay?", "call me when you can"]),
    ])
    _tara_zero_day(sc, date(2025, 1, 4), [
        ("08:50:20", ["good morning babu", "you up?"]),
        ("14:20:45", ["babu?", "hello", "reply na"]),
        ("21:35:10", ["phone dead?", "text me when you charge it", "love you"]),
    ])
    _tara_zero_day(sc, date(2025, 6, 14), [
        ("09:30:05", ["morning", "you alive?"]),
        ("16:05:40", ["hello??", "reply when you can", "i'm getting worried"]),
        ("23:20:15", ["just tell me you're okay", "one word is enough"]),
    ])

    # 7. Cindy (14 Mar 2025): Rohan says it, Tara replies four seconds later
    sc.convs.append(scene(date(2025, 3, 14), [
        ("22:58:30", R, "work was so long today"), ("23:01:00", T, "same. what happened"),
        ("23:06:00", R, "new project kickoff. endless"), ("23:06:45", T, "did you eat"),
        ("23:10:05", R, "yeah some sandwich"), ("23:11:40", T, "hmm"), ("23:20:00", R, "the new team is okay though"),
        ("23:21:00", T, "acha"), ("23:36:00", R, "my manager keeps praising the new hires"),
        ("23:42:17", R, "cindy from the new team is kinda cute ngl", ["cindy_original"]),
        ("23:42:21", T, "who is cindy", ["cindy_reply"]), ("23:42:48", R, "what"), ("23:42:55", T, "who. is. she."),
        ("23:44:10", R, "relax. nobody. she's just on my team"), ("23:47:30", T, "kinda cute ngl. interesting."),
        ("23:48:05", R, "i was just saying it out loud"), ("23:55:40", T, "to who"), ("23:56:02", R, "to you??"),
        ("24:00:15", T, "hmm"), ("24:02:40", R, "that's your answer to everything"), ("24:11:20", T, "i'm going to sleep"),
        ("24:12:00", R, "babu come on"), ("24:12:30", R, "it's nothing"), ("24:40:00", T, "goodnight"),
    ]))

    # 8. WhatsApp's own lines (they are not messages)
    sc.system = [
        (at(date(2024, 1, 3), "21:10:00"),
         "Messages and calls are end-to-end encrypted. Only people in this chat can read, listen to, or share them."),
        (at(date(2024, 9, 5), "10:00:00"),
         "Rohan changed their phone number to a new number. Tap to message or add the new number."),
        (at(date(2025, 3, 2), "08:15:00"), "Your security code with Tara changed. Tap to learn more."),
    ]

    # scenes must keep their distance from each other, exactly like free conversations
    probe = Schedule()
    for c in sorted(sc.convs, key=lambda c: c.start):
        assert probe.convs == [] or c.start - probe.convs[-1].end >= P.MARGIN, f"scenes too close at {c.start}"
        probe.add(c)
    return sc


def register(sched: Schedule, sc: Scenes) -> None:
    for c in sc.convs:
        sched.add(c)
    sched.forbidden.extend(sc.forbidden)
    sched.tara_zero_days |= sc.tara_zero_days
