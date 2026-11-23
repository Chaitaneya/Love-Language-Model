"""Copy: turning numbers into jokes (docs/STATS.md §5). Templates are plain strings with {slots}.

  ?key|template   only if values[key] is truthy      !key|template   only if it is falsy
  {q}             a quoted message, rendered from the chat by id (never generated); templates that need
                  one are skipped when no safe quote exists

Rules the banks follow (STATS §5.8): joke about behaviours, never about people; never state a feeling
as a fact; the number comes first and the line stays short."""

from __future__ import annotations

from datetime import date

from .context import A, B, Ctx
from .stats.base import Stat

# ------------------------------------------------------------------ formatting
_MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fmt_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} {_MON[d.month - 1]} {d.year}"


def fmt_dur(sec: float, coarse: bool = False) -> str:
    """1m 40s, 23 min, 2 h 10 min. Exports without seconds cannot resolve below a minute."""
    s = round(sec)
    if s < 60:
        return "under a minute" if coarse else f"{s}s"
    if s < 600:
        m, r = divmod(s, 60)
        return f"{m} min" if coarse or r == 0 else f"{m}m {r}s"
    if s < 3600:
        return f"{round(s / 60)} min"
    h, rem = divmod(s, 3600)
    m = round(rem / 60)
    if m == 60:
        h, m = h + 1, 0
    return f"{h} h" if m == 0 else f"{h} h {m} min"


def fmt_x(r: float) -> str:
    return "nearly 2×" if r < 2 else f"{round(r)}×"


def ordinal_comma(n: int) -> str:
    return f"{n:,}th"


def tier_of(r: float) -> str:
    return "mild" if r < 3 else "medium" if r < 6 else "extreme"


def format_context(stat: Stat, c: Ctx) -> dict:
    v = dict(stat.values)
    if v.get("q"):
        v["qe"] = "" if v["q"][-1] in ".?!…" else "."
    v["A"], v["B"] = c.name(A), c.name(B)
    if "r" in v:
        v["xs"] = fmt_x(v["r"])
    if "w" in v and "l" in v and v["w"] + v["l"]:
        v["pct_w"] = round(100 * v["w"] / (v["w"] + v["l"]))
    if "date" in v:
        v["date"] = fmt_date(v["date"])
    if "sec_fast" in v:
        coarse = v.get("coarse", False)
        v["dur_fast"], v["dur_slow"] = fmt_dur(v["sec_fast"], coarse), fmt_dur(v["sec_slow"], coarse)
    if v.get("dur") is not None:
        v["dur"] = fmt_dur(v["dur"], not c.chat.meta.has_seconds)
    if "top_a" in v:  # the winner's and loser's favourite emoji
        v["same"] = v["top_a"] == v["top_b"]
        v["top_w"], v["top_l"] = (v["top_a"], v["top_b"]) if v.get("win") == A else (v["top_b"], v["top_a"])
    if stat.id == "runtime_typing":
        d = v["days"]
        v["days_txt"] = (f"{d:g} days" if d >= 1.5 else f"{v['hours']} hours")
    if stat.id == "message_milestones":
        v["nth"] = ordinal_comma(v["n"])
    if stat.id == "signature_words":
        for k in range(3):
            v[f"wA{k + 1}"] = v["a"][k] if k < len(v["a"]) else ""
            v[f"wB{k + 1}"] = v["b"][k] if k < len(v["b"]) else ""
    if stat.id == "reel_dealer":
        v["thing"] = "reels" if v.get("reels") else "links"
    if "words" in v and isinstance(v["words"], (int, float)):
        v["words"] = int(v["words"])
    return v


# ------------------------------------------------------------------ the banks
# list = one tier; dict = {"mild": [...], "medium": [...], "extreme": [...], "any": [...]}
BANK: dict[str, list | dict] = {
    "messages_total": ["{n:,} messages. Somebody's thumbs deserve a day off.", "{n:,} messages and counting. Please seek daylight."],
    "span_days": ["{n} days of chat. Longer than most gym memberships.", "{n} days in, and the notifications have not stopped."],
    "msgs_per_day": ["{n} messages a day. On average. Every single day.", "{n} messages a day. That is a lot of typing for two people who live in the same timezone."],
    "words_total_books": ["{words:,} words together. That's {x:g} {unit}. {punch}"],
    "runtime_typing": ["{hours} hours of typing. That's {days_txt} of your life, thumbs only.", "Total typing time: {hours} hours. The thumbs deserve a salary."],
    "message_share": {
        "mild": ["{W} sends a little more than half the messages. The rest is commentary."],
        "any": ["{W} sends {pct}% of the messages. {L} sends the quality control."],
    },
    "peak_hour": [
        "?night|Most active hour: {hour_label}. Sleep is for people with fewer feelings.",
        "?night|{hour_label} is your most active hour. We hope you have curtains.",
        "?night|Peak hour: {hour_label}. Not a bug. A lifestyle.",
        "!night|Most active hour: {hour_label}. Suspiciously healthy.",
    ],
    "night_owl_share": [
        "{pct}% of your messages are sent between midnight and 5 AM. Concerning, but respectable.",
        "{W} sends {pct_w}% of their messages after midnight. Sleep is optional, apparently.",
    ],
    "early_bird": ["{W} sends {pct}% of their messages before 9 AM. Disturbing."],
    "longest_streak": ["{n} days without missing a day. Neither of you has a hobby.", "{n} days in a row. Not one day off. Not one."],
    "busiest_day": ["{date}: {n:,} messages in one day. That's {x}× a normal day.", "{n:,} messages on {date}. Something happened."],
    "goodnight_ritual": ["{W} said goodnight {w} times. {L}: {l}. Rituals matter."],
    "initiator": {
        "mild": ["{W} says hi first slightly more often. The race is on."],
        "medium": ["{W} starts {k} of every 10 conversations. {L} is 'waiting for the right moment.'"],
        "extreme": ["{W} starts {k} of every 10 conversations. {L} is 'waiting for the right moment.'",
                    "{W} starts {pct}% of your conversations. {L} just replies. Beautifully."],
    },
    "revival": ["When the chat goes quiet for a day, it's {W} who brings it back. {w} times to {l}."],
    "longest_monologue": [
        "?q|{W} once sent {n} messages in a row. {L} replied '{q}'{qe}",
        "?q|{n} messages in a row, from {W}. Then silence. Then '{q}'{qe}",
        "!q|{W} once sent {n} messages in a row. Nobody interrupted. Nobody could.",
    ],
    "double_texts": ["{W} double-texted {w:,} times. {L} did it {l:,}. The thumbs have spoken."],
    "words_per_message": ["{W} averages {w} words per message. {L}: {l}. One of you writes. One of you texts."],
    "one_word_replies": ["{pct}% of {W}'s messages are one word or less. Efficient. Terrifying."],
    "last_word": ["{W} gets the last word in {pct_w}% of your conversations. {L} has stopped arguing."],
    "questions": ["{W} asked {w:,} questions. {L} asked {l:,}. One of you is curious. One of you is tired."],
    "reply_median": {
        "mild": ["{fast} replies a bit faster than {slow}. Nobody is keeping score. (We are.)"],
        "medium": ["{fast} replies in {dur_fast}. {slow} replies in {dur_slow}. {slow} is 'busy.'"],
        "extreme": ["{fast} replies in {dur_fast}. {slow} replies in {dur_slow}. {slow} is 'busy.'",
                    "{slow} takes {xs} longer to reply. Somewhere, a notification is aging."],
    },
    "reply_fast_share": ["{pct}% of {W}'s replies arrive in under a minute. The phone never leaves the hand."],
    "left_hanging": ["{W} has ended {w} conversations with a question nobody answered. Hello? Hello?"],
    "first_ily": [
        "?plot_twist|It took {n} days for someone to say 'I love you'. It was {W}. Plot twist.",
        "?dur|{n} days in, {W} said 'I love you' first. {L} replied in {dur}.",
        "'I love you' arrived on day {n}. Sender: {W}. Cheers.",
        "!plot_twist|It took {n} days for someone to say 'I love you'. It was {W}.",
    ],
    "affection_count": ["{W} got sweet {w:,} times. {L}: {l:,}. Romance is not a competition. (It is.)"],
    "pet_name": ["'{token}' appears {n:,} times. Pet names: a love story.", "'{token}', {n:,} times. At this point it's a legal name."],
    "compliments": ["{W} paid {w} compliments. {L} paid {l}. Flattery will get you everywhere."],
    "makes_laugh": ["{W} makes {L} laugh {xs} as often as the reverse. Funniest in the house."],
    "signature_words": [
        "{A} says '{wA1}', '{wA2}' and '{wA3}'. {B} says '{wB1}', '{wB2}' and '{wB3}'. Distinct voices.",
        "Words only {A} says: {wA1}, {wA2}, {wA3}. Words only {B} says: {wB1}, {wB2}, {wB3}.",
    ],
    "ok_period": [
        "{n} instances of 'ok.' with a full stop. We hope everyone's okay.",
        "{W} has typed 'ok.' {n} times. That full stop is doing a lot of work.",
        "A full stop after 'ok'. {n} times, from {W}. In a text message.",
    ],
    "swearing": ["{n} naughty words in total. Mild, but noted.", "Your chat is rated {letter}. Wholesome-ish."],
    "emoji_top": ["{emoji} was used {n:,} times. It's basically a third participant.", "Top emoji: {emoji}, {n:,} times. Feelings were expressed."],
    "emoji_per_person": [
        "?same|{W} and {L} both reach for {top_w} first. Matching moods, apparently.",
        "!same|{W}'s emoji of choice: {top_w}. {L}'s: {top_l}. Different moods, same phone.",
    ],
    "reel_dealer": [
        "?reels|{W} has sent {w:,} links. {L}: {l:,}. Reels are a love language now.",
        "!reels|{W} has sent {w:,} links. {L}: {l:,}. The internet is a gift. Apparently.",
    ],
    "voice_notes": ["{W} sent {w:,} voice notes. {L} sent {l:,}. One of you has heard of typing."],
    "deleted": ["{W} deleted {w} messages. {L} deleted {l}. We'll never know."],
    "first_message": [
        "?q|First message ever: '{q}'{qe} Look at you now.",
        "!q|It started on {date}, with a message from {W}. Look at you now.",
    ],
    "message_milestones": [
        "?q|Message #{n:,}: '{q}'{qe} Poetic.",
        "?q|The {nth} message was sent by {W} on {date}. It said '{q}'{qe}",
        "!q|Message #{n:,} was sent by {W} on {date}. Somebody had to.",
    ],
    "longest_silence": ["The longest silence lasted {d} days. {W} broke it.", "{d} days without a word. Then {W} said hi."],
    "bang_then_silence": ["{date}: {n:,} messages. Then {d} days of silence. We have questions."],
    "apologies": ["{W} apologized {w:,} times. {L}, {l:,}. We're not saying anything. We're just saying."],
    "clingy_pings": ["{W} has sent a 'hello?'-style ping {w:,} times. {L}: {l:,}. One of you is watching the phone."],
    "triple_texts": ["{W} has triple-texted {w:,} times. At that point it's a newsletter."],
    "night_starter": ["{W} started {w:,} conversations after midnight. {L}: {l:,}. Nothing good happens at 2 AM."],
    "silence_breaker": [
        "?all|{W} broke every silence over 2 days. {k} out of {n}.",
        "!all|{W} broke {k} of the {n} silences over 2 days.",
    ],
    "fight_days": ["Days that looked like fights: {n}. First to apologize: {A} {a_first}, {B} {b_first}."],
    "who_is_that": ["{W} has asked 'who is' {w:,} times. {L} has asked it {l:,}."],
}


def _eligible(template: str, v: dict) -> str | None:
    if template[:1] in "?!" and "|" in template:
        key, body = template[1:].split("|", 1)
        if bool(v.get(key)) != (template[0] == "?"):
            return None
        return body
    return template


def render_stat(stat: Stat, c: Ctx) -> list[str]:
    """Every line variant that fits this stat's tier and facts. Quote-bearing variants need a safe quote."""
    bank = BANK.get(stat.id)
    if bank is None:
        return []
    v = format_context(stat, c)
    if isinstance(bank, dict):
        tier = tier_of(stat.values["r"]) if "r" in stat.values else "any"
        templates = list(bank.get(tier, [])) + list(bank.get("any", []))
    else:
        templates = list(bank)
    lines: list[str] = []
    for t in templates:
        body = _eligible(t, v)
        if body is None or ("{q}" in body and not v.get("q")):
            continue
        try:
            text = body.format_map(v)
        except (KeyError, IndexError, ValueError):
            continue
        if text not in lines:
            lines.append(text)
    return lines


# ------------------------------------------------------------------ poster pieces
CRITIC_SOURCES = {
    "volume": ["Their Phone Battery", "Their Thumbs", "The Keyboard"],
    "time": ["The Moon", "Their Alarm Clock", "Everyone With a Window"],
    "speed": ["{A}'s Thumbs", "{B}'s Notification Tray", "Do Not Disturb Mode"],
    "effort": ["The Neighbours", "Autocorrect", "The Space Bar"],
    "affection": ["Their Group Chat", "Mutual Friends", "The Heart Emoji"],
    "words": ["The Dictionary", "Autocorrect", "The Thesaurus"],
    "emoji": ["The Emoji Keyboard (Frequently Used)", "Their Thumbs"],
    "silence": ["The Void", "Airplane Mode", "Last Seen"],
    "apology": ["The Notes App", "Autocorrect", "The Draft Folder"],
    "milestone": ["The First Message", "Their Chat History"],
    "mystery": ["The Trash Can", "The Void"],
    "tone": ["The Full Stop", "Punctuation Police"],
    "streak": ["The Calendar", "Their Phone Battery"],
    "media": ["Their Camera Roll", "Their Data Plan"],
    "clingy": ["Last Seen", "Read Receipts"],
}

# (stat id, title template, condition). Spicy titles come first: they are the sharpest.
TITLES = [
    ("apologies", "SORRY {w}", lambda s, c: s.values.get("r", 0) >= 5),
    ("longest_silence", "THE {d}-DAY SILENCE", lambda s, c: c.spicy and s.values.get("d", 0) >= 3),
    ("peak_hour", "{hour_label} AND STILL TYPING", lambda s, c: s.values.get("night")),
    ("night_owl_share", "THE NIGHT SHIFT", lambda s, c: s.values.get("pct", 0) >= 30),
    ("longest_streak", "{n} DAYS, NO NOTES", lambda s, c: s.values.get("n", 0) >= 30),
    ("words_total_books", "THE COMPLETE WORKS OF {A} & {B}", lambda s, c: True),
    ("messages_total", "{n:,} MESSAGES LATER", lambda s, c: s.values.get("n", 0) >= 5000),
    ("reply_median", "THE LONG REPLY", lambda s, c: s.values.get("r", 0) >= 5),
    ("initiator", "SOMEONE HAS TO TEXT FIRST", lambda s, c: s.values.get("r", 0) >= 3),
]

TAGLINES = [
    "{messages:,} messages. {days} days. Zero chill.",
    "{days} days. {messages:,} messages. One of you is typing.",
    "Based on {words:,} words and a series of poor decisions.",
    "{per_day} messages a day. No notes.",
    "A love story in {messages:,} parts.",
]

FINE_PRINT_FIXED = "No chats were stored in the making of this poster."
FINE_PRINT_POOL = [
    "BASED ON A TRUE STORY. {messages:,} OF THEM.",
    "FILMED ENTIRELY ON LOCATION: YOUR PHONE.",
    "?double|NO DOUBLE TEXTS WERE HARMED. SEVERAL WERE SENT.",
    "THE FOLLOWING POSTER HAS BEEN APPROVED FOR ALL AUDIENCES EXCEPT YOUR PARENTS.",
]

REASONS = {  # rating-box phrases for countable stats
    "emoji_top": "{n:,} {emoji}",
    "pet_name": "?excessive|excessive use of \"{token}\"",
    "ok_period": "{n} passive-aggressive \"ok.\"s",
    "deleted": "{n} deleted messages",
    "swearing": "{n} naughty words",
    "reel_dealer": "{w:,} reels and links",
    "apologies": "{w:,} apologies",
    "double_texts": "{total:,} double texts",
}
