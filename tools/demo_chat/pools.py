"""Phrase pools for the demo couple. Generic pools must NEVER contain a word that the exact token
budgets or the signature seeds control (tests lint this): sorry/my bad, who is, cute, cindy, babu,
the profanity words, bro/scene/chalo/wait/hmm/literally/lowkey/acha/nahi, greetings and affection.
Those words enter the chat only through texts.py, in counted quantities."""

from __future__ import annotations

FOOD = ["biryani", "pizza", "maggi", "dosa", "momos", "pasta", "chai", "sandwich", "rolls", "burger",
        "pav bhaji", "idli", "noodles", "paratha", "pani puri"]
PLACE = ["the office", "the mall", "the gym", "the metro", "the cafe", "the station", "home",
         "the airport", "your place", "my place"]
WHEN = ["tomorrow", "tonight", "on saturday", "next week", "after work", "this weekend",
        "in the evening", "later today", "on sunday"]
THING = ["the project", "the report", "the deck", "my laptop", "the presentation", "the assignment",
         "my phone", "the charger", "the keys", "that email"]
TIME = ["five minutes", "ten minutes", "twenty minutes", "half an hour", "an hour"]
MEAL = ["breakfast", "lunch", "dinner"]

SHORT = [
    "haha", "hahaha", "lol", "lmao", "same", "true", "yeah", "yes", "no", "nope", "oh", "oh nice", "nice",
    "wow", "ugh", "really", "okay", "fine", "cool", "right", "makes sense", "fair", "exactly", "what",
    "why", "huh", "oh god", "never mind", "thanks", "please", "come on", "stop it", "shut up", "no way",
    "seriously", "that's crazy", "i know", "i see", "got it", "done", "perfect", "yay", "aww", "ohh", "uff",
    "arre", "haan", "haan yaar", "yaar", "kya", "kyun", "bas", "theek hai", "pagal hai tu", "abe",
    "oh come on", "hold on", "one sec", "give me a minute", "brb", "omg", "ayo", "oof", "yikes", "sure",
    "maybe", "later", "tomorrow", "tonight", "soon", "ya", "ya ya", "ohh okay", "ohh i see", "toh",
    "arre wah", "mast", "sahi hai", "sach mein", "thoda sa", "ek minute", "bas kar", "kya baat hai",
]

MEDIUM = [
    "did you eat anything today", "what are you doing right now", "i'm so tired today",
    "reached {place} just now", "stuck in traffic again", "this meeting will never end",
    "i'm starving honestly", "what should we have for {meal}", "my boss is being weird today",
    "i need coffee immediately", "are you free {when}", "i just saw the funniest thing",
    "can you call me later", "i'll call you in {time}", "send me the location",
    "i forgot {thing} at office", "my phone is at two percent", "the wifi is down again",
    "it's raining so hard here", "traffic on the bridge is insane", "i'm leaving in {time}",
    "did you take your medicine", "drink some water please", "have you slept at all",
    "i can't sleep tonight", 
    "i have a deadline {when}", "presentation went okay i think", "{meal} was so bad today",
    "ordering {food} {when}", "let's watch something {when}", "which episode are we on",
    "i'll book the tickets", "{when} plan works for me", "mom called me again",
    "my cousin's wedding is next month", "cab is taking forever", "reached the office finally",
    "the movie starts at nine", "come downstairs i'm outside", "i'll be there in {time}",
    "send me {thing} please", "did you see my last message", "you never reply when i'm free",
    "tell me everything", "i'm so annoyed right now", "this day is never ending", "i have so much work",
    "can you help me with {thing}", "remind me about {thing}", "i keep forgetting {thing}",
    "what time are you free", "are you at {place}", "i'm at {place} now", "i'm bored out of my mind",
    "what are we doing {when}", "i want {food} so badly", "let's get {food} {when}",
    "this {food} is amazing", "i miss {food} from that place", "{place} is so crowded today",
    "my back hurts from sitting all day", "the ac in the office is broken", "i'm walking home from the metro",
    "the lift is out of order again", "i spilled chai on my keyboard", "my neighbour is playing loud music",
]

QUESTIONS = [
    "what are you up to", "where are you", "are you coming", "did you reach", "when will you be free",
    "what's for dinner", "should i order", "what time is it there", "can you talk", "are you awake",
    "is everything okay", "did you see the news", "how was your day", "how was the meeting",
    "did you sleep well", "what did you do today", "do you want anything", "can you pick up the call",
    "are you angry", "why are you quiet", "what happened", "kya kar rahe ho", "kab aa rahe ho",
    "how's the weather there", "did you take a break", "what are you watching",
]

TOPIC_R = [
    "had leg day i can't walk", "did you see the match last night", "my bike is making a weird noise",
    "client call went on for two hours", "sprint review {when}", "ordered new headphones finally",
    "gym was packed today", "my protein shake tastes like chalk", "the standup could have been an email",
    "my team lead just changed the plan again", "laptop is hanging again", "fifa with the guys {when}",
    "my cricket team lost again", "bike service is due", "the new update broke everything",
    "debugging this since morning", "pushed the fix finally", "code review is brutal today",
]
TOPIC_T = [
    "this series is so good", "my skincare routine is a whole project", "found a nice cafe near office",
    "my order finally arrived", "design review got postponed", "i made a new playlist for the drive",
    "yoga class was brutal today", "my manager loves a last minute change", "the figma file is a mess",
    "finished the book finally", "book club is {when}", "thrifted the best jacket",
    "my plant is dying again", "my sister called for an hour", "the client hated the colour",
    "i have a headache since morning", "pilates tomorrow morning", "i'm making pasta tonight",
]

TOPIC_SHARED = TOPIC_R + TOPIC_T  # most topic talk is common ground; each person keeps a small private slice

EMOTION = [
    "you always do this", "i was just joking", "don't be dramatic", "i'm not being dramatic",
    "this is not a big deal", "can we not fight about this", "we'll talk when i'm home",
    "you never listen to me", "you're so annoying sometimes", "i'm tired of explaining",
    "you can't just say that", "that's not what i meant", "let's talk about it properly",
    "you promised you'd call", "i said i'd be late", "you're overthinking this", "i'm not mad",
    "i'm just a bit upset", "it's fine", "never mind it's not important",
]

CONNECT = [", and ", " but ", ", so ", ". also ", ", honestly ", ". anyway "]
PAD = ["honestly", "you know", "i think", "i guess", "anyway", "btw", "like", "seriously", "tbh", "for real", "i swear"]

ANSWERS = [
    "yeah", "no", "not yet", "later", "haan", "nope", "just now", "in ten minutes", "at home", "at office",
    "yes", "maybe", "i think so", "not really", "of course", "obviously", "barely", "kind of", "sort of",
    "still working", "on my way", "five minutes", "almost there", "nothing much", "just chilling",
    "watching something", "eating", "in a meeting", "stuck in traffic", "yeah just now", "haan bas", "no idea",
]
OPENERS = ["hey", "hi", "what's up", "you there", "kya haal", "hello", "yo", "free?", "busy?", "so", "guess what", "ugh"]

MULTILINE = [
    "things to buy:\nmilk\neggs\nbread\ncoffee",
    "okay so the plan:\nwe leave at six\nwe eat on the way\nyou drive\ni choose the music",
    "tonight's agenda\n- dinner\n- series\n- sleep",
    "roses are red\nviolets are blue\nyou take hours to reply\nand i'm still here too",
    "reminder for me:\ncall the plumber\nrecharge the phone\nbuy a birthday gift",
    "my day in three lines\nmeeting\nmeeting\nmore meetings",
    "the menu:\npasta\ngarlic bread\nsomething sweet if you're good",
    "list of things that annoyed me today\nthe cab driver\nthe lift\nthe lift again",
    "dear diary\ntoday i ate three samosas\nno regrets",
    "packing list\ncharger\nheadphones\njacket\nthat book you wanted",
    "quick update\nreached the hotel\nroom is tiny\nwifi works\nall good",
    "pros of staying home\nno traffic\nno people\nmore sleep",
    "movie options:\nthe thriller\nthe comedy\nthe one you picked last time",
    "i'll say this once\nyou matter to me\nmore than the work thing\nnow stop smiling",
    "rules for tonight:\nno phones at dinner\nno work talk\nno arguing about the thermostat",
    "status report\nfood: done\nmood: tired\nplans: sleep",
    "weekend ideas\nbeach\nold town walk\nstaying in bed",
    "today's wins\nfinished the report\ndrank water\nresisted ordering again",
    "shopping:\nrice\ndal\nonions\ntomatoes",
    "my honest review of today\ntwo out of ten\nwould not repeat",
    "note to self\nstop checking the phone\nstart checking the phone less\nsmall steps",
    "directions:\ntake the second left\npass the bakery\nthe blue building",
    "chai order\ntwo cups\nless sugar\nextra ginger",
]
assert len(MULTILINE) == 23

# ---- role texts (their words are budgeted in texts.py) ----
APOLOGY_R = ["sorry", "i'm sorry", "sorry okay", "sorry yaar", "sorry for being late", "sorry i got busy",
             "my bad", "sorry i was in a meeting", "sorry sorry", "really sorry", "sorry i missed your call"]
APOLOGY_T = ["sorry", "sorry i was busy", "sorry just saw this", "my bad", "sorry phone was on silent"]
WHO_IS = ["who is that", "who is she", "who is this guy", "who's this", "who is that again", "who is coming"]
LOVE = ["love you", "love you so much", "i love you", "luv u", "love u", "i love you a lot"]
MISS = ["miss you", "miss u", "i miss you so much", "missing you", "i miss you today"]
MORNING = ["good morning", "morning", "good morning sunshine", "gm", "just woke up", "waking up", "my morning is a disaster"]
NIGHT = ["good night", "goodnight", "gn", "sleep well", "good night sleep well", "going to sleep now", "sleeping now"]
LINK_LEAD = ["", "", "", "look at this", "this is us", "send this to everyone", "watch till the end", "mood", "same"]
SCENE_PH = ["kya scene hai", "scene on hai", "full scene", "scene set hai", "scene kya hai aaj ka"]
CHALO_PH = ["chalo", "chalo phir", "chalo bye", "chalo done", "chalo then"]
ACHA_PH = ["acha", "acha theek hai", "acha acha", "acha okay"]
NAHI_PH = ["nahi", "nahi yaar", "nahi nahi", "nahi pata"]
WAIT_PH = ["wait", "wait wait", "wait ruk", "wait a minute"]
HMM_PH = ["hmm", "hmm", "hmm hmm", "hmm okay"]

EMOJI_OTHER_R = [("😂", 0.032), ("🥺", 0.012), ("❤️", 0.015), ("😅", 0.008)]
EMOJI_OTHER_T = [("😂", 0.025), ("🙄", 0.015), ("😴", 0.010), ("🙈", 0.010), ("❤️", 0.008)]

# words the generic pools may not contain (enforced by tests/test_demo_chat.py)
RESERVED = [
    "sorry", "sry", "my bad", "maaf", "apolog", "forgive", "who is", "who's", "who’s", "kaun hai", "kon hai",
    "cute", "cindy", "sindy", "cindi", "pretty", "adorable", "good looking", "khana", "khaana", "khaya",
    "love you", "love u", "luv u", "miss you", "miss u", "missing you", "babu", "😭", "damn", "wtf", "crap",
    "bro", "scene", "chalo", "wait", "hmm", "literally", "lowkey", "acha", "nahi", "good morning",
    "good night", "goodnight", "gn", "gm",
]
