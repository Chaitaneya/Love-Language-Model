"""Every tunable of the demo generator in one place. The planted targets come from docs/STATS.md §6.3.
Timing knobs were calibrated by running tools/make_demo_chat.py --diagnose until the banded facts landed."""

from __future__ import annotations

from datetime import date, datetime, timedelta

SEED = 1234

R, T = "R", "T"  # internal sender keys
NAMES = {R: "Rohan", T: "Tara"}
OTHER = {R: T, T: R}

CHAT_START = date(2024, 1, 3)
CHAT_END = date(2025, 10, 23)
DAY_CUT = timedelta(hours=5)  # a chat day runs 05:00 -> 05:00

# --- exact targets (STATS §6.3) ---
TOTAL_MESSAGES = 47_382
TOTAL_BY = {R: 28_429, T: 18_953}
TARGET_WORDS = 283_000
FIGHT_DAY = date(2024, 8, 2)
FIGHT_MESSAGES = 1_204
MESSAGE_10000_WHEN = "wait what"

# --- conversation structure ---
CONV_GAP = timedelta(hours=4)  # the parser/stats threshold (STATS §0.3)
MARGIN = CONV_GAP + timedelta(seconds=60)  # generator keeps conversations strictly further apart than this
MAX_DELAY = 3 * 3600 + 30 * 60  # no gap inside a conversation reaches the 4 h threshold
CONV_CAP = int(4.2 * 3600)  # longest conversation, in seconds

TURN_MEAN = {R: 4.1492, T: 2.9747}  # mean messages per turn
TURN_CAP = {R: 14, T: 9}  # any turn must stay far below the planted 31-message monologue
SHORT_GAP = (7.0, 0.9)  # (median s, sigma): gap between messages of the same turn (always < 10 min)
LONG_GAP = (1500.0, 0.7)  # a double text: same sender, 10 min .. 2.5 h later, still no reply
P_DOUBLE = {R: 0.05853979351241487, T: 0.013023594323310395}  # chance a within-turn gap is a double-text gap
REPLY_R = (105.17861377807799, 1.15)  # Rohan replies: median ~100 s
REPLY_T_FAST = (45.0, 0.8)  # Tara replies are a mixture: engaged ...
REPLY_T_SLOW = (2936.0366054439432, 0.5)  # ... or busy
P_T_FAST = 0.38481925805002115  # -> overall median ~23 min
P_PING_CONV = 0.035  # share of Rohan-started conversations that are 1-3 unanswered messages

# --- daily schedule: three conversation classes per chat day ---
CLASS_P = {"A": 0.85, "B": 0.90, "C": 0.97}
CLASS_N = {"A": 25.95650461172298, "B": 36.734264477511786, "C": 27.476352656778797}  # median messages before the day multiplier
CLASS_WINDOW = {"A": (6.362384669163652, 10.079807014170624), "B": (11.318638148420904, 18.06307580586757), "C": (24.633468584246216, 26.349800263024132)}  # start window, hours after midnight
TEMPO = {"A": (1.7106851672145913, 0.8635), "B": (1.2181, 1.0824156326788477), "C": (1.8505581970409306, 0.55117879678979)}  # (edge, centre) delay multiplier per class
INITIATOR_ROHAN = 0.7035040714538917  # share of free conversations Rohan starts (STATS §6.3: 71% +-3)

# --- volume shape over time: messages-per-day multiplier by month ---
MONTH_MULT = {
    (2024, 1): 1.15, (2024, 2): 1.25, (2024, 3): 1.10, (2024, 4): 0.92, (2024, 5): 0.97,
    (2024, 6): 1.02, (2024, 7): 1.00, (2024, 8): 0.90, (2024, 9): 0.95, (2024, 10): 0.98,
    (2024, 11): 1.00, (2024, 12): 1.05, (2025, 1): 1.00, (2025, 2): 0.95, (2025, 3): 1.05,
    (2025, 4): 0.97, (2025, 5): 0.93, (2025, 6): 0.95, (2025, 7): 0.92, (2025, 8): 0.95,
    (2025, 9): 0.93, (2025, 10): 0.90,
}
WEEKEND_MULT = 1.12


def dt(y, m, d, hh=0, mm=0, ss=0) -> datetime:
    return datetime(y, m, d, hh, mm, ss)
