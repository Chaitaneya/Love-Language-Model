"""Stage 2 of the build: every plain slot becomes a message.

Counts the docs promise (STATS §6.3) are EXACT here: each budget is "target minus what scripted scenes
already contain", filled by picking slots without replacement. Generic phrase pools contain none of
the budgeted words (pools.RESERVED, linted in tests), so nothing else can change a count."""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime

from . import params as P
from . import pools as L
from .model import Slot
from .rng import Rng

R, T = P.R, P.T
ILY_DATE = datetime(2024, 2, 20)  # nothing affectionate before Tara's first "i love you"

# ---- the budgets (STATS §6.3) ----
TARGET = {
    "ok_dot": {R: 3, T: 38},
    "apology": {R: 214, T: 9},
    "who_is": {R: 3, T: 27},
    "cry": {R: 939, T: 1402},  # occurrences of 😭
    "babu": {R: 981, T: 293},  # occurrences of the word
    "deleted": {R: 41, T: 12},
    "audio": {R: 18, T: 160},
    "damn": {R: 90, T: 60},
    "wtf": {R: 60, T: 40},
    "crap": {R: 36, T: 24},
}
MEDIA = {  # not pinned by the docs, but they make an export look real
    "image": {R: 300, T: 430}, "sticker": {R: 180, T: 260}, "video": {R: 40, T: 35}, "gif": {R: 25, T: 20},
}
MEDIA_TEXT = {"image": "image omitted", "sticker": "sticker omitted", "video": "video omitted",
              "gif": "GIF omitted", "audio": "audio omitted"}
ROLE_COUNT = {  # slots given a fixed phrase list
    "multiline": {R: 9, T: 14}, "link": {R: 420, T: 90},
    "ily": {R: 200, T: 110}, "miss": {R: 160, T: 90}, "morning": {R: 100, T: 60}, "night": {R: 90, T: 60},
    "scene_ph": {R: 520, T: 10}, "chalo_ph": {R: 480, T: 8}, "wait_ph": {R: 250, T: 120},
    "hmm_ph": {R: 25, T: 600}, "acha_ph": {R: 60, T: 450}, "nahi_ph": {R: 90, T: 500},
}
INLINE = {  # signature words added to otherwise ordinary messages: (word, how, {sender: messages})
    "bro": ("affix", {R: 1200, T: 12}), "wait": ("prefix", {R: 200, T: 0}),
    "hmm": ("prefix", {R: 0, T: 700}), "literally": ("prefix", {R: 20, T: 700}), "lowkey": ("prefix", {R: 8, T: 400}),
}
EDITED = {R: 12, T: 13}

APOLOGY = re.compile(r"\b(sorry|sry|my bad|maaf|maafi|i apologi[sz]e|apologies|forgive me)\b", re.I)
WHO_IS = re.compile(r"\b(who is|who's|who’s|kaun hai|kon hai)\b", re.I)
BABU = re.compile(r"\bbabu\b", re.I)
_TOKEN = re.compile(r"\w+(?:['’]\w+)*")
_URL = re.compile(r"https?://\S+")
_SLOT = re.compile(r"\{(\w+)\}")

BUCKETS = {
    R: [("short", .34), ("medium", .22), ("q", .09), ("topic", .07), ("emo", .04), ("long", .14), ("para", .10)],
    T: [("short", .46), ("medium", .18), ("q", .08), ("topic", .06), ("emo", .05), ("long", .10), ("para", .07)],
}
LONG_BOOST = 1.79  # tuned so the natural word total lands on TARGET_WORDS (adjust_words then only trims a few)


def n_words(text: str) -> int:
    return len(_TOKEN.findall(_URL.sub(" ", text).lower()))


def measure(slots) -> Counter:
    """Budgeted quantities present in the given slots, keyed (what, sender)."""
    c: Counter = Counter()
    for s in slots:
        if s.kind != "text":
            c[("deleted" if s.kind == "deleted" else s.media_type, s.sender)] += 1
            continue
        t = s.text
        if APOLOGY.search(t):
            c[("apology", s.sender)] += 1
        if t.strip().lower() in ("ok.", "okay."):
            c[("ok_dot", s.sender)] += 1
        if WHO_IS.search(t):
            c[("who_is", s.sender)] += 1
        c[("cry", s.sender)] += t.count("😭")
        c[("babu", s.sender)] += len(BABU.findall(t))
        low = t.lower()
        for w in ("damn", "wtf", "crap"):
            c[(w, s.sender)] += len(re.findall(rf"\b{w}\b", low))
    return c


# ------------------------------------------------------------------ generic composition
def _fill(rng: Rng, tpl: str) -> str:
    pools = {"food": L.FOOD, "place": L.PLACE, "when": L.WHEN, "thing": L.THING, "time": L.TIME, "meal": L.MEAL}
    return _SLOT.sub(lambda m: rng.choice(pools[m.group(1)]), tpl)


def _topics(rng: Rng, sender: str) -> list[str]:
    own = L.TOPIC_R if sender == R else L.TOPIC_T
    return own if rng.chance(0.25) else L.TOPIC_SHARED


def _clause(rng: Rng, sender: str) -> str:
    r = rng.random()
    if r < 0.62:
        return _fill(rng, rng.choice(L.MEDIUM))
    if r < 0.82:
        return _fill(rng, rng.choice(_topics(rng, sender)))
    return rng.choice(L.EMOTION)


_QSET = set(L.QUESTIONS)


def compose(rng: Rng, sender: str, prev_text: str | None = None, opener: bool = False) -> str:
    """One ordinary message. `prev_text` is what the other person just said (so a question gets an
    answer-shaped reply); `opener` marks the first message of a conversation."""
    if opener and rng.chance(0.28):
        return rng.choice(L.OPENERS)
    if prev_text and (prev_text.rstrip().endswith("?") or prev_text in _QSET) and rng.chance(0.6):
        return rng.choice(L.ANSWERS)
    items = BUCKETS[sender]
    weights = [w * (LONG_BOOST if k in ("long", "para") else 1.0) for k, w in items]
    kind = rng.weighted([k for k, _ in items], weights)
    if kind == "short":
        return rng.choice(L.SHORT)
    if kind == "medium":
        return _fill(rng, rng.choice(L.MEDIUM))
    if kind == "q":
        q = rng.choice(L.QUESTIONS)
        return q + "?" if rng.chance(0.6) else q
    if kind == "topic":
        return _fill(rng, rng.choice(_topics(rng, sender)))
    if kind == "emo":
        return rng.choice(L.EMOTION)
    if kind == "long":
        return _clause(rng, sender) + rng.choice(L.CONNECT) + _clause(rng, sender)
    parts = [_clause(rng, sender) for _ in range(rng.randint(3, 4))]
    return ". ".join(parts)


def _reel(rng: Rng) -> str:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"
    code = "".join(alphabet[int(rng.random() * len(alphabet))] for _ in range(11))
    return f"https://www.instagram.com/reel/{code}/"


# ------------------------------------------------------------------ the planted one-offs (STATS §6.5)
def _d(y, m, d, hh=12, mm=0):
    return datetime(y, m, d, hh, mm)


PLANTED = [
    # Cindy: the original and Tara's reply are in scenes.py; these are the 12 later mentions
    (_d(2025, 3, 15, 18), T, "so how's cindy", ["cindy_mention"]),
    (_d(2025, 3, 21, 12), R, "cindy sent me the deck lol", ["cindy_mention"]),
    (_d(2025, 4, 3, 19), T, "does cindy sit near you", ["cindy_mention"]),
    (_d(2025, 4, 19, 21), T, "tell cindy i said hi", ["cindy_mention"]),
    (_d(2025, 5, 8, 11), R, "cindy is on leave this week", ["cindy_mention"]),
    (_d(2025, 6, 2, 20), T, "cindy ka birthday hai kya", ["cindy_mention"]),
    (_d(2025, 6, 27, 22), T, "yeah ask sindy about it", ["cindy_mention", "cindy_variant"]),
    (_d(2025, 7, 14, 13), R, "cindyy and her cat videos again", ["cindy_mention", "cindy_variant"]),
    (_d(2025, 8, 9, 19, 30), T, "invite cindy too i guess", ["cindy_mention"]),
    (_d(2025, 9, 1, 12, 30), R, "cindy got promoted btw", ["cindy_mention"]),
    (_d(2025, 9, 18, 20), T, "wow cindi gets everything", ["cindy_mention", "cindy_variant"]),
    (_d(2025, 10, 5, 21), T, "is cindy coming to the party", ["cindy_mention"]),
    # people other than Tara called pretty / adorable / good looking: no literal "cute" (semantic search set)
    (_d(2024, 4, 9, 15), R, "that actress in the new ad is so pretty", ["cute_paraphrase"]),
    (_d(2024, 7, 3, 20), T, "your friend's baby is adorable", ["cute_paraphrase"]),
    (_d(2024, 10, 26, 13), R, "the new barista is good looking honestly", ["cute_paraphrase"]),
    (_d(2025, 1, 18, 21), T, "that guy from your gym is good looking not gonna lie", ["cute_paraphrase"]),
    (_d(2025, 5, 12, 14), R, "her dog is adorable", ["cute_paraphrase"]),
    (_d(2025, 8, 30, 22), T, "the waiter was so pretty i stared", ["cute_paraphrase"]),
    # the literal word "cute" elsewhere (keyword search finds these, and the Cindy message)
    (_d(2024, 5, 30, 21, 30), R, "you looked so cute today babu", ["cute_literal"]),
    (_d(2024, 12, 2, 22), R, "your cute face on that video call", ["cute_literal"]),
    (_d(2025, 2, 14, 8, 30), R, "happy valentines my cute babu", ["cute_literal"]),
    (_d(2024, 9, 11, 19), T, "that puppy video is so cute", ["cute_literal"]),
    (_d(2025, 6, 21, 18), T, "look at this cute cat", ["cute_literal"]),
    # Hinglish spelling variants of one question (fuzzy-search set)
    (_d(2024, 3, 8, 20), R, "khana khaya?", ["khana"]),
    (_d(2024, 3, 9, 21), T, "khaana khaya kya", ["khana"]),
    (_d(2024, 6, 21, 14), R, "khana kha liya?", ["khana"]),
    (_d(2025, 2, 2, 13), T, "khaya kya", ["khana"]),
    (_d(2025, 4, 26, 21, 30), R, "khana khaya yaar", ["khana"]),
]


class _Pool:
    """Plain slots per sender in a fixed random order; each take() hands out distinct unassigned slots."""

    def __init__(self, slots: list[Slot], rng: Rng):
        self.by = {R: [], T: []}
        for s in slots:
            if not s.protected and not s.role:
                self.by[s.sender].append(s)
        for lst in self.by.values():
            rng.shuffle(lst)

    def take(self, sender: str, n: int, pred=None) -> list[Slot]:
        out = []
        for s in self.by[sender]:
            if n <= 0:
                break
            if s.role or (pred and not pred(s)):
                continue
            out.append(s)
            n -= 1
        if n > 0:
            raise RuntimeError(f"not enough plain slots for sender {sender}")
        return out


def _assign(slot: Slot, role: str, text: str = "", kind: str = "text", media: str | None = None) -> None:
    slot.role, slot.text, slot.kind, slot.media_type = role, text, kind, media


def realize(slots: list[Slot], rng: Rng) -> None:
    # 1. planted one-offs: the first free slot of the right sender on or after the target time
    for when, sender, text, tags in PLANTED:
        slot = next(s for s in slots if s.sender == sender and s.ts >= when and not s.protected and not s.role)
        _assign(slot, "planted", text)
        slot.protected = True
        slot.tags.extend(tags)

    have = measure([s for s in slots if s.protected])  # what the scenes and planted messages already hold
    pool = _Pool(slots, rng.fork("pool"))
    trng = rng.fork("text")

    def need(what: str, who: str) -> int:
        n = TARGET[what][who] - have[(what, who)]
        if n < 0:
            raise RuntimeError(f"scenes already exceed the budget for {what}/{who}")
        return n

    # 2. kinds that are not text
    for who in (R, T):
        for s in pool.take(who, TARGET["deleted"][who]):
            _assign(s, "deleted", "You deleted this message." if who == R else "This message was deleted.", "deleted")
        for s in pool.take(who, TARGET["audio"][who]):
            _assign(s, "media", MEDIA_TEXT["audio"], "media", "audio")
        for kind, per in MEDIA.items():
            for s in pool.take(who, per[who]):
                _assign(s, "media", MEDIA_TEXT[kind], "media", kind)

    # 3. exact-count phrases
    multi = list(L.MULTILINE)
    rng.fork("multi").shuffle(multi)
    for who in (R, T):
        for s in pool.take(who, need("ok_dot", who)):
            _assign(s, "ok_dot", "ok.")
        for s in pool.take(who, need("apology", who)):
            _assign(s, "apology", trng.choice(L.APOLOGY_R if who == R else L.APOLOGY_T))
        for s in pool.take(who, need("who_is", who)):
            _assign(s, "who_is", trng.choice(L.WHO_IS))
        for s in pool.take(who, ROLE_COUNT["multiline"][who]):
            _assign(s, "multiline", multi.pop())
        for s in pool.take(who, ROLE_COUNT["link"][who]):
            lead = trng.choice(L.LINK_LEAD)
            _assign(s, "link", (lead + " " if lead else "") + _reel(trng))
        late = lambda s: s.ts >= ILY_DATE
        hour_ok = {
            "ily": late, "miss": late,
            "morning": lambda s: s.ts >= ILY_DATE and 6 <= s.ts.hour < 11,
            "night": lambda s: s.ts >= ILY_DATE and (s.ts.hour >= 22 or s.ts.hour < 4),
        }
        for role, phrases in (("ily", L.LOVE), ("miss", L.MISS), ("morning", L.MORNING), ("night", L.NIGHT)):
            for s in pool.take(who, ROLE_COUNT[role][who], hour_ok[role]):
                text = trng.choice(phrases)
                if who == R and trng.chance(0.35):
                    text += " babu"
                _assign(s, role, text)
        for role, phrases in (("scene_ph", L.SCENE_PH), ("chalo_ph", L.CHALO_PH), ("wait_ph", L.WAIT_PH),
                              ("hmm_ph", L.HMM_PH), ("acha_ph", L.ACHA_PH), ("nahi_ph", L.NAHI_PH)):
            for s in pool.take(who, ROLE_COUNT[role][who]):
                _assign(s, role, trng.choice(phrases))

    # what is now fixed (scenes, planted messages and every role above) already holds part of each
    # budget; the modifiers below fill only what is left
    have.clear()
    have.update(measure([s for s in slots if s.protected or s.role]))

    # 4. everything left is ordinary talk
    generic = [s for s in slots if not s.protected and not s.role]
    is_generic = {id(s) for s in generic}
    prev: Slot | None = None
    for s in slots:  # time order, so a reply can see what it replies to
        if id(s) in is_generic:
            same_conv = prev is not None and prev.conv == s.conv
            reply_to = prev.text if same_conv and prev.sender != s.sender and prev.kind == "text" else None
            _assign(s, "generic", compose(trng, s.sender, reply_to, opener=not same_conv))
        prev = s
    gpool = _Pool.__new__(_Pool)
    gpool.by = {w: [s for s in generic if s.sender == w] for w in (R, T)}
    for lst in gpool.by.values():
        rng.fork("gshuffle").shuffle(lst)

    def pick(who: str, n: int, pred=None) -> list[Slot]:
        out = []
        for s in gpool.by[who]:
            if n <= 0:
                break
            if "mod:" + str(id(pred)) in s.tags or (pred and not pred(s)):
                continue
            out.append(s)
            n -= 1
        if n > 0:
            raise RuntimeError("not enough generic slots")
        return out

    mrng = rng.fork("mods")
    for who in (R, T):
        # signature words
        for word, (how, counts) in INLINE.items():
            for s in pick(who, counts[who]):
                if how == "prefix" or (how == "affix" and mrng.chance(0.5)):
                    s.text = f"{word} {s.text}"
                else:
                    s.text = f"{s.text} {word}"
                s.tags.append("mod")
        # the pet name
        for s in pick(who, need("babu", who), lambda s: s.ts >= ILY_DATE):
            s.text = f"babu {s.text}" if mrng.chance(0.2) else f"{s.text} babu"
            s.tags.append("mod")
        # the crying emoji: k occurrences per message, summing exactly to the budget
        remaining = need("cry", who)
        while remaining > 0:
            k = min(remaining, mrng.weighted([1, 2, 3], [0.85, 0.10, 0.05]))
            s = pick(who, 1)[0]
            s.text = f"{s.text} {'😭' * k}"
            s.tags += ["mod", "cry"]
            remaining -= k
            gpool.by[who].remove(s)  # one 😭 message per slot
        # mild swearing, counted
        for word, lead in (("damn", "damn "), ("wtf", "wtf "), ("crap", "oh crap ")):
            for s in pick(who, need(word, who)):
                s.text = lead + s.text
                s.tags.append("mod")
        # edited markers
        for s in pick(who, EDITED[who]):
            s.edited = True
            s.tags.append("edited")

    # 5. a sprinkle of other emoji (not budgeted)
    erng = rng.fork("emoji")
    for s in generic:
        for emo, p in (L.EMOJI_OTHER_R if s.sender == R else L.EMOJI_OTHER_T):
            if emo == "❤️" and s.ts < ILY_DATE:
                continue
            if erng.chance(p):
                s.text += " " + emo
                break


def adjust_words(slots: list[Slot], rng: Rng) -> int:
    """Nudge the total word count onto TARGET_WORDS by padding or trimming untouched generic messages."""
    free = [s for s in slots if s.role == "generic" and not s.tags and s.kind == "text"]
    total = sum(n_words(s.text) for s in slots if s.kind == "text")
    diff = P.TARGET_WORDS - total
    i = 0
    rng.shuffle(free)
    guard = 0
    while abs(diff) > 25 and guard < 200_000:
        guard += 1
        s = free[i % len(free)]
        i += 1
        if diff > 0:
            word = rng.choice(L.PAD)
            s.text = f"{s.text} {word}" if rng.chance(0.5) else f"{word} {s.text}"
            diff -= n_words(word)
        else:
            parts = s.text.split(" ")
            if len(parts) >= 5:
                diff += n_words(parts[-1])
                s.text = " ".join(parts[:-1])
    return P.TARGET_WORDS - diff


def assert_budgets(slots: list[Slot]) -> dict:
    got = measure(slots)
    report = {}
    for what, per in list(TARGET.items()):
        for who, want in per.items():
            assert got[(what, who)] == want, f"budget {what}/{who}: wanted {want}, got {got[(what, who)]}"
            report[f"{what}/{P.NAMES[who]}"] = want
    return report
