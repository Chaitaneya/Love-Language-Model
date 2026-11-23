"""Tunable constants. What each one means: docs/STATS.md section 0.3 and docs/decision.md D14."""

# --- ingest / parsing ---
DETECT_SAMPLE_LINES = 500          # non-empty lines examined when detecting the export format
LEADING_JUNK_MAX = 10              # the first header must appear within this many non-empty lines
LOW_MATCH_WARN = 0.5               # below this share of header lines, warn (never block: multi-line messages)
MAX_ARCHIVE_BYTES = 200 * 1024 * 1024  # refuse zip members that claim to expand beyond this
MIN_MESSAGES = 300                 # below this the chat is a "trailer", not a movie

# --- stats (used from M3 on) ---
CONV_GAP_HOURS = 4                 # gap that starts a new conversation
DAY_CUT_HOUR = 5                   # a "chat day" ends at 5 AM
DOUBLE_GAP_MINUTES = 10            # same-sender follow-up after this long counts as a double text
SILENCE_HOURS = 48                 # gap that counts as "a silence"
WPM = 36                           # mobile typing speed (Palin et al., MobileHCI 2019: 36.2 WPM)
