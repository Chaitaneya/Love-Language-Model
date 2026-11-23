# STATS — the stat catalog, the jokes, and the demo couple

Companion to [PRD.md](PRD.md). The PRD says *what* we build. This doc says what we **measure**, how each number is **computed**, how the poster **picks** what to show, how the numbers become **jokes**, and which **fake couple** we test everything on.

Status: Draft v0.1 · 21 Nov 2026

---

## 0. How to read this

### 0.1 The 14 lines I'd bet the project on

These are the lines the demo couple produces (§6). If a stat can't produce something this good, cut it.

| # | Line | Stat |
|---|---|---|
| 1 | "It took 47 days for someone to say 'I love you'. It was Tara. Plot twist." | `first_ily` |
| 2 | "Rohan replies in 1m 40s. Tara replies in 23 min. Tara is 'busy.'" | `reply_median` |
| 3 | "Rohan once sent 31 messages in a row. Tara replied 'hmm'." | `longest_monologue` |
| 4 | "Rohan apologized 214 times. Tara, 9. We're not saying anything. We're just saying." | `apologies` (spicy) |
| 5 | "38 instances of 'ok.' with a full stop. We hope everyone's okay." | `ok_period` |
| 6 | "2 Aug 2024: 1,204 messages. Then 6 days of silence. We have questions." | `bang_then_silence` (spicy) |
| 7 | "Most active hour: 2 AM. Sleep is for people with fewer feelings." | `peak_hour` |
| 8 | "283,000 words together. That's 6 Great Gatsbys. Old sport." (the book is a seeded pick: a reroll may say 3.7 Philosopher's Stones or 3 Hobbits) | `words_total_books` |
| 9 | "Message #10,000: 'wait what'. Poetic." | `message_milestones` |
| 10 | "Rohan deleted 41 messages. Tara deleted 12. We'll never know." | `deleted` |
| 11 | "Rohan broke every silence over 2 days. 4 out of 4." | `silence_breaker` (spicy) |
| 12 | "Rohan starts 7 of every 10 conversations. Tara is 'waiting for the right moment.'" | `initiator` |
| 13 | "131 hours of typing. That's 5½ days of your life, thumbs only." | `runtime_typing` |
| 14 | "Tara has asked 'who is' 27 times. Rohan has asked it 3." | `who_is_that` (spicy) |

What makes these work (use these as the review checklist for every new line):
1. **Real number first, deadpan second.** The number does the work. The line only frames it.
2. **Understatement beats exaggeration.** "We have questions." beats "OMG what happened?!".
3. **The reveal is a behavior, not a verdict.** Nobody is called unlovable. Someone *replied "hmm"*.
4. **A small twist or callback** where possible (#1: the ghost says it first; #6: the 6 days).
5. **Short.** Critic lines ≤ 90 characters. Say the joke, stop.

### 0.2 Stat card format

Every stat in §1 has these fields:

| Field | Meaning |
|---|---|
| `id` | Stable identifier. Used in code, the JSON contract and test names. |
| `pri` | P0 = build first (≈ 14 stats, enough for the whole poster). P1 = Director's Cut + poster candidates. P2 = Director's Cut only, or later. |
| `kind` | `couple` (one number for the pair), `versus` (A vs B), `event` (one specific moment), `viz` (chart only). |
| `n_min` | Minimum sample. Below it, the stat skips itself. A stat never shows a number it can't back up. |
| `wow` | The value at which the stat scores 1.0 (§4.1). |
| `valence` | How the subject feels about it: **F** flattering, **N** neutral, **U** unflattering. Used for the fairness rule (§4.3). |
| `theme` | Slot de-duplication group (§4.2). |
| `spicy` | Hidden unless Spicy mode is on. |

### 0.3 Constants (all tunable, all in one `config.py`)

| Constant | Value | Why |
|---|---|---|
| `CONV_GAP` | 4 h | Gap that starts a new conversation. Sensitivity-tested at 2 h and 6 h (§6.6). |
| `DAY_CUT` | 5 AM | A "chat day" ends at 5 AM, not midnight. Couples don't sleep at midnight. |
| `DOUBLE_GAP` | 10 min | A same-sender follow-up after this long with no reply counts as a double text. |
| `NIGHT` | 00:00–04:59 | Night hours. |
| `EARLY` | 05:00–08:59 | Early-bird hours. |
| `WPM` | 36 | Average mobile typing speed: 36.2 WPM in Palin et al., MobileHCI 2019 (37,370 volunteers). [Study page](https://userinterfaces.aalto.fi/typing37k). Rounded down. |
| `SILENCE` | 48 h | Gap that counts as "a silence". |
| `MIN_CHAT` | 300 messages | Below this, show the "trailer" error. |

---

## 1. Definitions and the stat catalog

### 1.0 Definitions (everything below uses exactly these)

- **Message:** a non-system line. `kind` is `text`, `media`, `deleted` or `call`. "Text stats" use `text` only.
- **Token / word:** after removing URLs, tokens are matched by `\w+(?:['’]\w+)*` (Unicode-aware) on lowercase text. Emoji are counted separately, never as words. `words` = token count over text messages.
- **Squash (matching only):** to match lexicon entries, collapse any run of repeated letters to one on **both** the lexicon entry and the text ("babuuu" → "babu", "sorryyy" → "sory", "sorry" → "sory"). Never shown to users.
- **Turn:** a maximal run of consecutive messages from one sender.
- **Conversation:** consecutive messages are in the same conversation if the gap is < `CONV_GAP`.
- **Chat day:** the date of (timestamp − 5 h).
- **Active day:** a chat day where **both** people sent ≥ 1 text message.
- **Streak:** a run of calendar-consecutive active days. `longest_streak` is the longest one.
- **Reply:** a turn change inside a conversation, from X to Y. `reply_time` = first message time of Y's turn − last message time of X's turn, clamped at ≥ 0, attributed to Y. The first turn of a conversation is an **initiation**, not a reply.
- **Initiation:** the first message of a conversation, attributed to its sender.
- **Double text:** inside one turn, a message whose gap from the sender's previous message is ≥ `DOUBLE_GAP` and < `CONV_GAP`. (Sender followed up and still got no reply.) A **triple text** is a second such gap in the same turn.
- **Last word:** the sender of the last message of a conversation.
- **Question message:** a text message containing `?`.

### 1.1 Volume

| id | pri | kind | Definition | n_min | wow | valence | theme |
|---|---|---|---|---|---|---|---|
| `messages_total` | P0 | couple | Count of non-system messages | 300 | 50,000 | N | volume |
| `span_days` | P0 | couple | `(last_date − first_date).days` (not inclusive) | 14 | 730 | N | volume |
| `msgs_per_day` | P1 | couple | `messages_total / span_days` | 14 d | 100 | N | volume |
| `words_total_books` | P1 | couple | `words`, compared to the book table (§5.7). Skips if smaller than the smallest book. | 5,000 | 4× the best-fit book | N | volume |
| `runtime_typing` | P0 | couple | `words / WPM / 60` hours. Display "N hrs". Also shown as days when ≥ 48 h. | 5,000 | 200 h | N | volume |
| `message_share` | P1 | versus | Each person's share of messages | 300 | 5× | N | effort |

### 1.2 Time and rhythm

| id | pri | kind | Definition | n_min | wow | valence | theme |
|---|---|---|---|---|---|---|---|
| `peak_hour` | P0 | couple | Hour of day (0–23) with the most messages. Only *interesting* if in `NIGHT`: score × 0.3 otherwise. | 1,000 | share 10% | N | time |
| `night_owl_share` | P0 | versus | Share of each person's messages sent in `NIGHT`. Also couple-level: total night share. | 500 | 40% (couple) / 5× (versus) | N | time |
| `early_bird` | P2 | versus | Share of each person's messages in `EARLY` | 500 | 5× | F | time |
| `longest_streak` | P0 | event | Longest streak of active days (§1.0). Reports start date, end date, length. | 14 d | 100 days | F | streak |
| `busiest_day` | P1 | event | Chat day with the most messages: date, count | 14 d | 10× median day | N | volume |
| `goodnight_ritual` | P2 | versus | Count of messages matching the goodnight lexicon, per person | 20 | 5× | F | affection |
| `heartbeat` | P0 | viz | Messages per calendar month (poster ECG line) | 2 mo | — | — | — |
| `hour_heatmap` | P1 | viz | Messages by weekday × hour | 1,000 | — | — | — |

### 1.3 Effort and initiation

| id | pri | kind | Definition | n_min | wow | valence | theme |
|---|---|---|---|---|---|---|---|
| `initiator` | P0 | versus | Initiations per person | 20 convs | 5× | F (subject: starter) | effort |
| `revival` | P1 | versus | Initiations after a gap ≥ 24 h, per person | 8 | 5× | F | effort |
| `longest_monologue` | P0 | event | Longest turn by message count, inside one conversation. Reports sender, length, the first message of the reply turn (the "reply"), and its time gap. | 8 msgs | 30 | N (subject: sender) | effort |
| `double_texts` | P1 | versus | Double-text count per person | 50 | 5× | N (subject: doubler) | effort |
| `words_per_message` | P1 | versus | Mean tokens per text message, per person | 200 | 3× | N | effort |
| `one_word_replies` | P2 | versus | Share of a person's text messages with ≤ 1 token | 200 | 5× | N | effort |
| `last_word` | P2 | versus | Last-word share per person | 20 convs | 3× | N | effort |
| `questions` | P2 | versus | Question messages per person | 100 | 3× | F | effort |

### 1.4 Replies

| id | pri | kind | Definition | n_min | wow | valence | theme |
|---|---|---|---|---|---|---|---|
| `reply_median` | P0 | versus | **Median** `reply_time` per person (never the mean: sleep ruins means). Subject = the slower person. Display `< 1 min` below 60 s (Android has minute resolution, PRD §11.6). | 100 replies each | 5× | U (subject: slower) | speed |
| `reply_fast_share` | P2 | versus | Share of replies < 1 min | 100 | 3× | F | speed |
| `left_hanging` | P2 | versus | Conversations whose last message is a question message from X (X got no answer) | 10 | 5× | N | speed |

### 1.5 Words and affection

Lexicons are plain JSON in `lexicons/` (editable by contributors), matched after squashing (§1.0).

| id | pri | kind | Definition | n_min | wow | valence | theme |
|---|---|---|---|---|---|---|---|
| `first_ily` | P0 | event | First message matching the `i_love_you` lexicon (phrases only: "i love you", "love you", "love u", "luv u", plus Hinglish forms). Reports sender, date, `days_since_first`. **Skips if it occurs in the first message** (just a greeting). | 1 | fixed 0.9 | F | milestone |
| `affection_count` | P1 | versus | Messages per person matching `affection` lexicon (love/miss phrases, pet names, hearts emoji) | 30 | 5× | F | affection |
| `pet_name` | P1 | couple | Auto-detected pet name: the non-stopword token that most often follows a love phrase or greeting ("love you ___", "good morning ___", "hi ___"). It needs ≥ 20 such follows **and** those follows must be ≥ 3% of all its uses (so "today", which merely follows "miss you" now and then, is not a pet name). Falls back to the editable list (baby, babe, babu, jaan, shona, …) at ≥ 20 uses. Reports the token and its total count. | 20 | 500 | F | affection |
| `compliments` | P2 | versus | Messages per person matching the `compliment` lexicon (cute, pretty, handsome, beautiful, gorgeous, …) | 15 | 5× | F | affection |
| `signature_words` | P0 | versus | Top words per person by log-odds z-score (§2) | 5,000 words | z = 8 | N | words |
| `makes_laugh` | P1 | versus | For each person X: laughter tokens (haha, lol, lmao, 😂, 🤣, …) in Y's message that is the reply to X's turn, within 2 min. Subject = the one who produces more laughter in the other. | 50 | 3× | F | affection |
| `ok_period` | P1 | versus | Messages whose normalized text is exactly `ok.` or `okay.` (a lone full stop is the point), per person | 5 | 5× | U | tone |
| `swearing` | P1 | couple | Messages matching `profanity` lexicon per 1,000 words (drives the rating letter, §5.6). The list is never printed. | 5,000 words | rate 6 | N | tone |
| `caps_lock` | P2 | versus | Messages of ≥ 5 letters in ALL CAPS, per person | 10 | 5× | N | tone |
| `lowercase_rebel` | P2 | versus | Share of text messages beginning with a lowercase letter | 200 | 2× | N | tone |

### 1.6 Emoji and media

| id | pri | kind | Definition | n_min | wow | valence | theme |
|---|---|---|---|---|---|---|---|
| `emoji_top` | P0 | couple | Most used emoji across the chat (Unicode grapheme clusters, so skin-tone and ZWJ sequences count once). Reports emoji and count. Rating-box candidate. | 100 emoji | 1,500 | N | emoji |
| `emoji_per_person` | P1 | versus | Each person's top emoji and emoji per message | 100 | 3× | N | emoji |
| `reel_dealer` | P1 | versus | URL count per person; domains grouped (instagram reels, youtube, etc.) | 30 | 5× | N | media |
| `voice_notes` | P2 | versus | "audio omitted" count per person. **iOS exports only**; skips on Android. | 20 | 5× | N | media |
| `deleted` | P1 | versus | Deleted-message markers per person ("This message was deleted", "You deleted this message") | 10 | 3× | N | mystery |

### 1.7 Milestones and events (the combos)

| id | pri | kind | Definition | n_min | wow | valence | theme |
|---|---|---|---|---|---|---|---|
| `first_message` | P0 | event | The first non-system message: sender, text, date. Quote only if ≤ 6 words and passes the quote guard (§5.5). | 1 | fixed 0.8 | F | milestone |
| `message_milestones` | P1 | event | The message at positions 1,000 / 5,000 / 10,000 / 25,000 / 50,000 / 100,000: sender, date, text (if quote-safe). Among reached milestones of at least 5,000 whose message makes a safe quote, one is picked with the seed (a reroll can show another); otherwise the largest. | 1,000 | fixed 0.7 | F | milestone |
| `longest_silence` | P1 | event | Largest gap between consecutive messages (≥ `SILENCE`): length in whole empty calendar days, who sent the last message before, who broke it | 1 gap | 6 days | U | silence |
| `anniversary` | P2 | event | Message count on each anniversary of the first message | 1 yr | fixed 0.5 | F | milestone |
| `new_year_midnight` | P2 | event | Who sent the first message after 00:00 on 1 Jan, and how many seconds after | 1 | fixed 0.5 | F | milestone |
| `bang_then_silence` | P1 | event (combo) | Busiest day whose next ≥ 3 chat days have no messages: date, count, silent days. The "fight day" detector. | 1 | fixed 0.95 | U | silence |

### 1.8 Spicy (opt-in; the poster always still gets ≥ 1 wholesome line)

| id | pri | kind | Definition | n_min | wow | valence | theme |
|---|---|---|---|---|---|---|---|
| `apologies` | P1 | versus | Messages per person matching the `apology` lexicon (sorry, my bad, maaf, I apologize, …). One count per message. | 20 | 5× | U | apology |
| `clingy_pings` | P1 | versus | Messages per person matching the `ping` lexicon ("??", "hello?", "reply", "where are you", "kaha ho", "busy?", …) | 20 | 5× | U | clingy |
| `triple_texts` | P1 | versus | Triple-text events per person | 10 | 5× | U | clingy |
| `night_starter` | P2 | versus | Initiations in `NIGHT`, per person | 10 | 5× | N | clingy |
| `silence_breaker` | P1 | versus | Of the silences ≥ `SILENCE`, who sent the first message after each. Reports "k of n". | 3 silences | all of ≥ 4 | U | silence |
| `fight_days` | P2 | event | Days with message count ≥ 5× the median day **and** ≥ 2 apology-lexicon messages. Reports the count and who apologized first on how many. Labeled "days that looked like fights". | 1 | fixed 0.8 | U | apology |
| `who_is_that` | P2 | versus | Messages per person matching "who is", "who's", "kaun hai", "kon hai" (question form) | 10 | 5× | N | clingy |

Spicy rules: never combine two Spicy lines on the same person on the poster (§4.3); Spicy mode raises the rating one level and adds the suffix "and mild emotional damage" (§5.6).

---

## 2. Word analysis: the signature words and the word cloud

### 2.1 Why not a plain frequency cloud
A frequency cloud of a couple's chat is "I / you / haha / ok" in different sizes. It says nothing. The interesting question is **"which words are this person's, and not the partner's?"** That is a solved problem, and the method has a great name: **Fightin' Words** (Monroe, Colaresi & Quinn, 2008).

### 2.2 Method: log-odds with an informative Dirichlet prior
For each token `w`, with counts `y_A(w)`, `y_B(w)` and totals `n_A`, `n_B`:

```
α_w   = α0 · (y_A(w) + y_B(w)) / (n_A + n_B)         # prior: pooled usage, total strength α0
δ(w)  = ln[(y_A+α_w) / (n_A+α0−y_A−α_w)] − ln[(y_B+α_w) / (n_B+α0−y_B−α_w)]
σ²(w) ≈ 1/(y_A+α_w) + 1/(y_B+α_w)
z(w)  = δ(w) / σ(w)                                    # z > 0: A's word; z < 0: B's word
```

- Start with `α0 = 500` and tune on the demo couple (§6). Treat it as a hyperparameter, not a law.
- Candidate tokens: pooled count ≥ 8, after the filters in §2.3.
- Keep `|z| ≥ 2.0`. Top 5 per person → `signature_words` stat. Top 40 → cloud.
- Why this and not tf-idf or raw ratios: raw ratios crown rare typos ("a word said once by one person"). The prior shrinks low counts toward "no difference", so only words with enough evidence rise. This is a good paragraph for the README.

### 2.3 Filters (what keeps the cloud from being boring or embarrassing)
1. **Stopwords:** English + Hinglish lists in `lexicons/stopwords.json`: i, you, the, a, hai, ka, ki, ke, … (function words only: "nahi", "acha" and "chalo" are not stopwords, they are the demo's signature words). Kept short and editable. Without these, the cloud is all "the".
2. **Not tokens:** URLs, numbers, tokens of 1 character, placeholders (`omitted`, `deleted`).
3. **Participants' own names and pet names** are allowed. They are the couple's vocabulary.
4. **Probable third-party proper nouns are hidden by default.** Heuristic: a token that appears capitalized in the original text in ≥ 80% of its uses and is not at the start of a sentence, and is not a participant name. The cloud is meant for sharing, so *Cindy* shouldn't be in it by accident. Toggle: "Show names".
5. **Tap a word to redact it** (it becomes a black bar, like poster lines). State is in memory only.
6. **Emoji** are allowed in the cloud as tokens (toggle, default on). Rendering of emoji on canvas varies; test on iOS.

### 2.4 Modes
| Mode | Words | Color | Use |
|---|---|---|---|
| **Dueling** (default) | Top 40 per person by `z` (size ∝ `√|z|`) | Person's color | The funny one: *his words vs her words* |
| **Shared** | Words both use a lot: rank by `min(y_A, y_B)` among non-stopwords (size ∝ `√min`) | One color | Sweet: *"your" vocabulary* |

Both come from the same table, so Shared is almost free.

### 2.5 Data contract (Python → JS)
```json
"words": {
  "dueling": {
    "A": [{"w": "bro", "z": 9.1, "nA": 405, "nB": 7}],
    "B": [{"w": "hmm", "z": -8.4, "nA": 12, "nB": 388}]
  },
  "shared": [{"w": "literally", "nA": 211, "nB": 240}],
  "tokens": {"A": 142310, "B": 140690}
}
```
Layout is JS: `d3-cloud` or `wordcloud2.js` (pick one in M0 and check its license and version), seeded RNG so the same reroll gives the same layout, display font from the poster, on canvas. Python never draws.

### 2.6 Where it appears
- **Director's Cut (v1):** both modes, with the redact tap.
- **Share card #2 (v2):** the Dueling cloud in a heart-shaped mask, person names as headers, 9:16, same export path as the poster.
- **Not on the poster.** It is already full, and a cloud fights the photo for attention.

### 2.7 Demo expectation (test)
Seeds planted in the demo (§6.4): Rohan = {bro, scene, chalo, sorry, wait}, Tara = {hmm, literally, acha, lowkey, nahi}. Test: the top 5 per person by `z` must contain ≥ 4 of these 5.

---

## 3. Meters and archetypes

### 3.1 Honesty statement (shown in the UI)
These meters count **text behaviors** that people read as caring or clingy. They cannot measure feelings. A person who prefers calls, works 9-to-6, or types in bursts will score "wrong". Every meter has a *How we calculated this (badly)* expander with the exact formula below. The meters live in Director's Cut, never on the poster.

### 3.2 Shares, not scores
There is no baseline for "a normal couple", so every component is a **share between the two partners**, with Laplace smoothing:

```
share_c(A) = (a_c + 1) / (a_c + b_c + 2)        share_c(B) = 1 − share_c(A)
meter(A)   = 100 · Σ w_c · share_c(A)           meter(B) = 100 − meter(A)
```

A component that misses its `n_min` is dropped and the remaining weights are renormalized.

### 3.3 Love-o-meter ("who shows it more, in text")

| Component | Weight | Source |
|---|---|---|
| Affection phrases, pet names, hearts | 0.30 | `affection_count` |
| Starting conversations | 0.20 | `initiator` |
| Reply speed | 0.15 | share of `1 / median reply time` |
| Words written | 0.10 | total `words` |
| Questions asked | 0.10 | `questions` |
| Compliments | 0.10 | `compliments` |
| Goodnights | 0.05 | `goodnight_ritual` |
| **Total** | **1.00** | |

Verdict bands (subject = the higher scorer, "Rohan"; template §5.9):

| Meter(A) | Band | Verdict style |
|---|---|---|
| 45–55 | balanced | *"Perfectly balanced. As all things should be. Suspicious."* |
| 55–65 | lean | *"{W} shows a bit more. {L} is not exactly absent."* |
| > 65 | clear | *"{W} shows more, in text. That is all this measures."* |

The verdict never contains the words "loves less", "doesn't care" or a bare percentage as the headline. The number appears on a tug-of-war bar with the label "text effort".

### 3.4 Clingy-meter (Spicy only)

Components use **rates per 1,000 of that person's own messages** (so the person who sends more isn't automatically clingier), then shares:

| Component | Weight | Source |
|---|---|---|
| Double texts | 0.25 | `double_texts` |
| Pings ("??", "hello?", "reply") | 0.20 | `clingy_pings` |
| Triple texts | 0.15 | `triple_texts` |
| Breaking silences | 0.15 | `silence_breaker` |
| Apologies | 0.15 | `apologies` |
| Night-time conversation starts | 0.10 | `night_starter` |
| **Total** | **1.00** | |

Verdicts are labels, not insults: *"Level: Notification Enthusiast"*, *"Level: Phone Face-Down"*, *"Level: Mutual Chaos"*. Behavior names, not a personality diagnosis.

### 3.5 Archetypes (the billing block)

Each person is given **one** archetype. The pair always gets two different ones.

**Score** of archetype `k` for person `X`: `score = min(1, ln(ratio_k) / ln(5)) × confidence`, where `ratio_k` is X's value divided by the partner's value for the archetype's defining stat (inverted where "lower" is the point). An archetype needs `score ≥ 0.25` to qualify.

**Assignment:** build the (person × archetype) score matrix. A **strong fit** (score ≥ 0.85) is ranked by editorial priority, the funniest first (lower number), then by score; a weaker fit is ranked by score alone. The best claim across both people is assigned first, then the other person gets their best remaining archetype. **Why:** two archetypes that both fit someone that well are separated by noise, not by data. This rule exists because the sensitivity test (§6.6) flipped Tara from The Ghost to The Voice-Note Enthusiast at a 2 h conversation gap, on a score difference of 0.04.

| Archetype | Defining stat | Valence | Priority (lower = funnier, editorial) | Spicy only | Blurb (Director's Cut) |
|---|---|---|---|---|---|
| THE DOUBLE TEXTER | `double_texts` higher | N | 2 | no | Sends the follow-up. Always. |
| THE GHOST | `reply_median` slower **and** `initiator` lower | U | 1 | no | Present, in the way weather is present. |
| THE PARAGRAPH WRITER | `words_per_message` higher | N | 4 | no | Texts like they're being billed by the word. |
| THE ONE-WORD WONDER | `one_word_replies` higher | N | 4 | no | "k" is a complete thought. |
| THE 3 AM PHILOSOPHER | `night_owl_share` higher | N | 3 | no | Deep thoughts, shallow sleep. |
| THE EARLY BIRD | `early_bird` higher | F | 6 | no | Good morning, unprompted. Disturbing. |
| THE EMOJI MACHINE | `emoji_per_person` rate higher | N | 4 | no | Nothing said without a face attached. |
| THE INTERVIEWER | `questions` higher | F | 5 | no | Asks. Listens. In that order. |
| THE INITIATOR | `initiator` higher | F | 4 | no | Someone has to say hi first. |
| THE LAST WORD | `last_word` higher | N | 5 | no | The conversation ends when they say so. |
| THE REEL DEALER | `reel_dealer` higher | N | 5 | no | Communicates entirely in videos of cats. |
| THE VOICE-NOTE ENTHUSIAST | `voice_notes` higher (iOS only) | N | 5 | no | Why type when you can monologue. |
| THE COMEDIAN | `makes_laugh` higher | F | 3 | no | Gets the laugh. Counts them. |
| THE HOPELESS ROMANTIC | `affection_count` higher | F | 3 | no | Says it. Out loud. In text. |
| THE APOLOGIST | `apologies` higher | U | 2 | **yes** | Sorry. Sorry about that too. |
| THE NOTIFICATION ENTHUSIAST | `clingy_pings` higher | U | 2 | **yes** | Has seen your "last seen". |
| THE LEAD / THE OTHER LEAD | fallback when nothing qualifies | F | 9 | no | Two main characters. No supporting cast. |

Fairness (§4.3): if both assigned archetypes are U, replace the lower-scoring one with the best F or N archetype for that person.

---

## 4. Selection: which stats make the poster

### 4.1 Scoring

For every eligible stat (min sample met, spicy gate respected):

```
base:
  couple  : clip( (ln v − ln meh) / (ln wow − ln meh) )  with meh = wow / 20
            (shares, i.e. peak_hour and night_owl_share, use the linear excess over the uniform baseline:
             on a log scale a perfectly flat chat would already score 0.7)
  versus  : clip( ln r / ln R_wow )   r = (max + 1)/(min + 1), R_wow from the `wow` column
  event   : the fixed score in the catalog, or wow-scaled where a wow is given
confidence  c = 1 − exp(−n / n0)         n0 = n_min · 2
score       = base × c
```

Every stat returns `score`, `values`, `subject`, `valence`, `theme`, `quote_ids` and its rendered `lines`.

**Rank = round(score, 2) × charm.** `charm` is an editorial weight, from 0.45 for `msgs_per_day` up to 1.0 for the best jokes (`reply_median`, `longest_monologue`, `first_ily`, `apologies`). Without it a dozen stats tie at exactly 1.0 on the demo and the choice would be arbitrary. Scores equal to two decimals are ties, broken by charm, then by stat id. (Rounding matters: `peak_hour` once lost the title to `reply_median` by 0.00000000005.)

### 4.2 Slot filling (greedy, in this order)

| Order | Slot | Takes | Rule |
|---|---|---|---|
| 1 | **Laurel** | Best of: `longest_streak`, `longest_monologue`, `busiest_day`, `bang_then_silence`, `longest_silence`, `message_milestones` (ties in that order) | First, so that an equally extreme award stat cannot be spent as a critic quote. |
| 2 | **Top critic** | Highest rank among **F** valence stats | Must exist; if none, the best N stat. Wholesome first, always. Countable stats are not used here: they are saved for the rating box. |
| 3 | **Title** | Best-scoring eligible title template (§5.3) | Based on the stat's own score. |
| 4 | **Tagline** | Random (seeded) from the pool whose slots are all available | Needs `messages_total` and `span_days`. |
| 5 | **Critic ×2** | Top two remaining by score | Distinct `theme`s. Distinct from themes already used. |
| 6 | **Billing** | Archetype assignment (§3.5) | Two different archetypes. |
| 7 | **Rating box** | The top 3 remaining *countable* stats by rank (`emoji_top`, `pet_name`, `ok_period`, `deleted`, `reel_dealer`, `swearing`; `apologies` and `double_texts` only in Spicy mode), listed in a fixed reading order | Spicy adds "mild emotional damage" and raises the letter one level. |
| 8 | **Fixed** | Release date, runtime, fine print | From pools. |

### 4.3 The fairness rule (the thing that stops the poster from bullying one person)
- **At most one U-valence line per person** across the whole poster (laurel + critics). Spicy mode allows two.
- A line's subject is the person it *describes* (the winner by default; for `reply_median` the slower person; for `longest_monologue` the sender).
- When the best candidate would be the second U line for someone, skip to the next-best candidate.
- At least one line must be F. If every candidate is U or N, the poster shows N lines only.
- At most one line per theme.

### 4.4 Reroll, swap, hide (PRD §7.5)
- **Reroll:** new seed; changes variant picks and tie-breaks only, never the stats' values. Reproducible by seed.
- **Swap:** a critic quote shows the next five candidates that pass the same rules.
- **Hide:** replaces the line with `[REDACTED]`; the stat is excluded for this session.

---

## 5. Copy: turning numbers into jokes

### 5.1 Template syntax

| Slot | Meaning |
|---|---|
| `{A}` `{B}` | The two names (after the Who's-who step) |
| `{W}` `{L}` | Winner / loser (by the stat's subject rule) |
| `{w}` `{l}` | Winner's / loser's value; `{x}` = ratio shown as "7×" (rounded; "nearly 2×" if < 2) |
| `{n}` | A count, formatted with thousands separators |
| `{dur}` | A duration: `2 min`, `1m 40s`, `4 h 10 min`. Below 60 s on Android-resolution data: `under a minute` |
| `{q}` | A quoted message, rendered from the chat by ID. ≤ 6 words, passes the quote guard (§5.5). The template is dropped if no safe quote exists. |

Tier by ratio: **mild** < 3×, **medium** 3–6×, **extreme** ≥ 6×. Each stat has 2–3 variants (P0) or ≥ 1 (P1/P2), picked by the seeded RNG. Lines are written so they can be pasted into a critic quote.

### 5.2 Copy bank, P0 stats

**`first_ily`** (F)
- "It took {n} days for someone to say 'I love you'. It was {W}. Plot twist." *(when the sender is the slower replier or less affectionate partner)*
- "{n} days in, {W} said 'I love you' first. {L} replied in {dur}."
- "'I love you' arrived on day {n}. Sender: {W}. Cheers."

**`reply_median`** (U, subject = slower)
- mild: "{W} replies a bit faster than {L}. Nobody is keeping score. (We are.)"
- medium: "{fast} replies in {dur_fast}. {slow} replies in {dur_slow}. {slow} is 'busy.'"
- extreme: "{slow} takes {x} longer to reply. Somewhere, a notification is aging."

**`longest_monologue`** (N)
- "{W} once sent {n} messages in a row. {L} replied '{q}'."
- "{n} messages in a row, from {W}. Then silence. Then '{q}'."
- (no safe quote) "{W} once sent {n} messages in a row. Nobody interrupted. Nobody could."

**`initiator`** (F)
- medium/extreme: "{W} starts {k} of every 10 conversations. {L} is 'waiting for the right moment.'"
- mild: "{W} says hi first slightly more often. The race is on."

**`peak_hour`** (N; only if in `NIGHT`)
- "Most active hour: {hour}. Sleep is for people with fewer feelings."
- "{hour} is your most active hour. We hope you have curtains."
- "Peak hour: {hour}. Not a bug. A lifestyle."

**`longest_streak`** (F)
- Laurel: `WINNER · LONGEST STREAK · {n} DAYS` · Critic: "{n} days without missing a day. Neither of you has a hobby."

**`runtime_typing`** (N)
- "{n} hours of typing. That's {d} days of your life, thumbs only."
- "Total typing time: {n} hours. A full-time job takes less."

**`messages_total` / `span_days` / `msgs_per_day`** (taglines, §5.3)

**`emoji_top`** (rating box + critic)
- Rating reason: "{n} {emoji}"
- Critic: "{emoji} was used {n} times. Only one person is ever crying."

**`signature_words`** (N)
- "{A} says '{wA1}', '{wA2}' and '{wA3}'. {B} says '{wB1}', '{wB2}' and '{wB3}'. Distinct voices."
- "Words only {A} says: {wA1}, {wA2}, {wA3}. Words only {B} says: {wB1}, {wB2}, {wB3}."

**`first_message`** (F)
- "First message ever: '{q}'. Look at you now." *(only with a safe quote)*

### 5.3 Titles and taglines

**Titles** (pick the template whose source stat scores highest; uppercase in design):

| Source stat | Template | Condition |
|---|---|---|
| `peak_hour` | `{hour} AND STILL TYPING` | hour in `NIGHT` |
| `night_owl_share` | `THE NIGHT SHIFT` | couple night share ≥ 30% |
| `longest_streak` | `{n} DAYS, NO NOTES` | n ≥ 30 |
| `words_total_books` | `THE COMPLETE WORKS OF {A} & {B}` | exists |
| `messages_total` | `{n} MESSAGES LATER` | n ≥ 5,000 |
| `reply_median` | `THE LONG REPLY` | ratio ≥ 5 |
| `initiator` | `SOMEONE HAS TO TEXT FIRST` | ratio ≥ 3 |
| `apologies` *(spicy)* | `SORRY {n}` | ratio ≥ 5 |
| `longest_silence` *(spicy)* | `THE {d}-DAY SILENCE` | d ≥ 3 |

**Taglines** (seeded random from those whose slots are available):
- "{messages}. {days} days. Zero chill."
- "{days} days. {messages} messages. One of you is typing."
- "Based on {words} words and a series of poor decisions."
- "{msgs_per_day} messages a day. No notes."
- "A love story in {messages} parts."

**Fine print** (the last line; one is fixed, one random):
- Fixed: "No chats were stored in the making of this poster."
- Pool: "BASED ON A TRUE STORY. {messages} OF THEM." · "FILMED ENTIRELY ON LOCATION: YOUR PHONE." · "NO DOUBLE TEXTS WERE HARMED. SEVERAL WERE SENT." *(only if `double_texts` exists)* · "THE FOLLOWING POSTER HAS BEEN APPROVED FOR ALL AUDIENCES EXCEPT YOUR PARENTS."

### 5.4 Copy bank, P1 and spicy (one tier each, add variants after the poster ships)

| Stat | Line |
|---|---|
| `apologies` | "{W} apologized {w} times. {L}, {l}. We're not saying anything. We're just saying." |
| `ok_period` | "{w} instances of 'ok.' with a full stop. We hope everyone's okay." |
| `bang_then_silence` | "{date}: {n} messages. Then {d} days of silence. We have questions." |
| `longest_silence` | "The longest silence lasted {d} days. {W} broke it." |
| `silence_breaker` | "{W} broke every silence over 2 days. {k} out of {n}." |
| `double_texts` | "{W} double-texted {w} times. {L} did it {l}. The thumbs have spoken." |
| `triple_texts` | "{W} has triple-texted {w} times. At that point it's a newsletter." |
| `clingy_pings` | "{W} has sent '??' {w} times. {L}: {l}. One of you is looking at the phone." |
| `who_is_that` | "{W} has asked 'who is' {w} times. {L} has asked it {l}." |
| `message_milestones` | "Message #{n}: '{q}'. Poetic." / "The {n}th message was sent by {W} on {date}. It said '{q}'." |
| `deleted` | "{W} deleted {w} messages. {L} deleted {l}. We'll never know." |
| `words_total_books` | "{words} words together. That's {x} {book}. {punch}" (§5.7) |
| `words_per_message` | "{W} averages {w} words per message. {L}: {l}. One of you writes. One of you texts." |
| `makes_laugh` | "{W} makes {L} laugh {x} as often as the reverse. Funniest in the house." |
| `reel_dealer` | "{W} has sent {w} links. {L}, {l}. Reels are a love language now." |
| `night_owl_share` | "{W} sends {pct}% of their messages between midnight and 5 AM. Concerning, but respectable." |
| `pet_name` | "'{token}' appears {n} times. Pet names: a love story." |
| `busiest_day` | "{date}: {n} messages in one day. That's {x} a normal day." |
| `longest_silence` (variant) | "{d} days without a single message. Then {W} said '{q}'." |

### 5.5 Quote guard (what may appear as a quoted message on the poster)
A message is eligible as a poster quote only if all hold:
1. ≤ 6 words.
2. No URLs, phone numbers, e-mail addresses, or digits sequences ≥ 4.
3. No probable third-party proper noun (the same heuristic as §2.3 item 4; participant names are allowed).
4. Passes the profanity filter (it can still be in the data; just never the poster).
5. If the Quotes toggle is off, no quotes at all.
Rendered by message ID from the parsed chat. Never retyped, never generated. (PRD §3.2.)

The Exhibit A evidence card is exempt from guards 1–4: the user chose that exact message on purpose.

A quote that ends in punctuation does not get the sentence's own full stop (`'hi, is this Tara?' Look at you now.`), via the `{qe}` slot.

**Known limit.** The proper-noun heuristic only catches names that are capitalised somewhere and never lowercase. In a chat typed entirely in lowercase ("cindy"), a third-party name passes the guard. Mitigations that exist: one switch turns all quotes off, every poster line can be hidden, and the cloud lets users tap a word to redact it. Revisit with real samples.

### 5.6 Rating box
- **Letter:** from `swearing` rate per 1,000 words: **G** < 0.5 · **PG** < 2 · **PG-13** < 6 · **R** ≥ 6. Spicy mode raises one level.
- **Reasons:** top 3 *countable* stats in the phrase "for {r1}, {r2} and {r3}" (e.g., `2,341 😭`, `excessive use of "babu"`, `38 passive-aggressive "ok."s`). "Excessive use" is chosen when the stat scored ≥ 0.6.
- Spicy suffix: "…and mild emotional damage."
- Design: a generic bordered box. No real rating logos. (PRD §7.4.)

### 5.7 Book table (`lexicons/books.json`)
Word counts are approximate and vary by edition; **verify in Spike 0** and display rounded.

| Book | ≈ Words | Punchline |
|---|---|---|
| The Great Gatsby | 47,000 | "Old sport." |
| Harry Potter and the Philosopher's Stone | 77,000 (the commonly cited count is 76,944; [search result](https://gitnux.org/harry-potter-books-statistics/)) | "Nobody asked for the sequel." |
| The Hobbit | 95,000 | "There and back again. Repeatedly." |
| The Lord of the Rings (trilogy) | 480,000 | "At least they got a ring." |
| War and Peace | 560,000 | "Tolstoy would like a word. Not another word, though." |

Rule: candidates are the books whose multiple `x = words / book` is between 1.5 and 12 (falling back to any book ≥ 1×); one is picked with the seed, so a reroll can say "3.7 Philosopher's Stones" or "3 Hobbits". `x` is shown with up to one decimal ("6", "3.7"). If `words` is below the smallest book, the stat skips itself. Every punchline must work for any multiple.

### 5.8 Tone rules (the lint list)
- Joke about **behaviors** (double texting, 2 AM, "ok."). Never about appearance, money, family, health, religion, sex, or whether someone is loved. (PRD §3.6.)
- A person is never named as the worst. Lines name a behavior, then the person.
- Max one pop-culture reference per poster.
- Critic sources are objects and abstractions, never real people or brands.
- No line may state or imply a *feeling* as measured fact ("X doesn't love Y", "X is obsessed"). Allowed: "X sends more", "X replies slower".
- Spicy is opt-in, off by default, and has its own copy tier. Verdict lines in Spicy mode remain labels, not diagnoses.
- Star ratings: F lines ★★★★★, N lines ★★★★☆, U lines ★★☆☆☆ to ★★★☆☆ (seeded), Spicy U lines ★☆☆☆☆.

### 5.9 Critic source pool (by theme; chosen with the seeded RNG)

| Theme | Sources |
|---|---|
| volume | Their Phone Battery · Their Thumbs · The Keyboard |
| time | The Moon · Their Alarm Clock · Everyone With a Window |
| speed | {A}'s Thumbs · {B}'s Notification Tray · Do Not Disturb Mode |
| effort | The Neighbours · Autocorrect · The Space Bar |
| affection | Their Group Chat · Mutual Friends · The Heart Emoji |
| words | The Dictionary · Autocorrect · The Thesaurus |
| emoji | The Emoji Keyboard (Frequently Used) · Their Thumbs |
| silence | The Void · Airplane Mode · The Last Seen |
| apology | The Notes App · Autocorrect · The Draft Folder |
| milestone | The First Message · Their Chat History |
| mystery | The Trash Can · The Void |

---

## 6. The demo couple: Rohan & Tara

The demo exists for one reason: a recruiter should see a great poster in one click. It is also the **golden test fixture** for every stat, search and parser path.

### 6.1 Cast
- **Rohan** — 28 — the Double Texter. Fast replier, night owl, apologizes, uses "bro", "scene", "chalo", "sorry", "wait".
- **Tara** — 27 — the Ghost with a secret soft side. Slow replier, dry ("hmm", "ok."), "literally", "lowkey", "acha", "nahi". Says "I love you" first.
- Hinglish sprinkled in (kya, acha, nahi, chalo, jaan, babu). Code-mixed on purpose: it stress-tests lexicons and Exhibit A.
- A third character, **Cindy** (a coworker), appears in the Exhibit A planted story (§6.5). Fully fictional.

### 6.2 Scale and format
- 3 Jan 2024 → 23 Oct 2025. `span_days` = 659.
- **47,382 messages**, 282,976 words, **3.06 MB** as text (0.51 MB gzipped), generated in about half a second. The output is committed as `demo/demo_chat.txt` (decision D13 is closed: no need to generate it in the browser).
- Written in **iOS format** (`[03/01/24, 9:14:08 PM] Rohan: …`, date order DMY, 12 h clock with seconds and a narrow no-break space before AM/PM). The other export formats are covered by the round-trip writers in `core/tests/helpers.py`, not by this generator.

### 6.3 Planted facts

Three kinds. **Exact:** placed by the generator on purpose; tests assert equality. **Budgeted:** the generator is given a quota up front and fills it exactly. **Banded:** produced by stochastic filler; tests assert a tolerance.

| Fact | Value | Kind |
|---|---|---|
| Total messages (non-system) | 47,382 (Rohan 28,429 · Tara 18,953) | Budgeted |
| Span | 3 Jan 2024 → 23 Oct 2025 (659 days) | Exact |
| First message | Rohan, 3 Jan 2024, 9:14:08 PM: "hi, is this Tara?" | Exact |
| First "I love you" | Tara, 19 Feb 2024 (day 47) | Exact |
| Longest monologue | Rohan, **31** messages, 14 Jun 2024, ~1:12–1:49 AM; Tara's next message "hmm" at ~2:09 AM | Exact |
| Longest streak | **183** days, 2 Feb → 2 Aug 2024 (a one-sided day on 1 Feb 2024 ends the first streak, which ran 29 days; one-sided days on 4 Jan 2025 and 14 Jun 2025, plus the extra silences, keep every later streak at 160 days or fewer) | Exact |
| Busiest day | 2 Aug 2024: **1,204** messages; last message of the day is Tara: "ok." | Exact |
| Silence after it | 6 empty days (3–8 Aug); broken by Rohan on 9 Aug, 9:10 PM: "hey" | Exact |
| Silences ≥ 48 h | 4 (the one above, plus three more); **all 4** broken by Rohan | Exact |
| 10,000th message | Tara: "wait what" (11 May 2024) | Exact |
| `ok.` (lone, with full stop) | Tara 38 · Rohan 3 | Budgeted |
| 😭 | 2,341 total (Tara 1,402 · Rohan 939) | Budgeted |
| "babu" | 1,274 total (Rohan 981 · Tara 293) | Budgeted |
| Apology-lexicon messages | Rohan 214 · Tara 9 | Budgeted |
| Deleted markers | Rohan 41 · Tara 12 | Budgeted |
| "audio omitted" (voice notes) | Tara 160 · Rohan 18 | Budgeted |
| "who is" questions | Tara 27 · Rohan 3 | Budgeted |
| Double texts | **measured:** Rohan 1,067 · Tara 123 (total 1,190). Band: total 1,100–1,300 and Rohan > 7× Tara | Banded |
| Median reply | **measured:** Rohan 100 s (band 95–105, "1m 40s") · Tara 1,375 s (band 1,250–1,510, "23 min") | Banded |
| Initiation share | **measured:** Rohan 69.2% (band 68–74%) | Banded |
| Peak hour | **measured:** 2 AM at 10.5%; runner-up 3 AM at 7.5%. Band: share ≥ 8.5% and a lead of ≥ 1.5 points over every other hour | Banded |
| Night share (00:00–04:59) | **measured:** 34.2% (band ≥ 30%) | Banded |
| Total words | **measured:** 282,976 (band 283,000 ±1,500; → 131.0 h at 36 WPM) | Banded |
| Mild swearing | damn 150 · wtf 100 · crap 60 = 310 words = 1.10 per 1,000 → rating **PG** | Budgeted |

Also measured on the committed demo: 1,739 conversations (2.68 a day), 71.9 messages a day, a second-longest streak of 124 days, and 648 chat days with at least one message. The bands for double texts, the peak-hour margin and initiation were **loosened after the generator existed**: the first guesses (total ±5%, runner-up hour ≤ 7.5%) were set before anything could be measured. The banded numbers are calibrated for seed 1234 only.

Sanity checks on those numbers (all verified): 47 days after 3 Jan 2024 is 19 Feb 2024; 283,000 words at 36 WPM is 131.0 hours; the 183-day streak ends exactly on the busiest day; and 283,000 ÷ 77,000 ≈ 3.7 Philosopher's Stones.

### 6.4 Voice (so the stats are not just correct but legible)
- Signature seeds: Rohan {bro, scene, chalo, sorry, wait}, Tara {hmm, literally, acha, lowkey, nahi}. Test: ≥ 4 of 5 appear in each person's top-5 (§2.7).
- Pet name: "babu" follows "love you", "good morning" and "hi" often enough for the auto-detector (§1.5) to find it without the fallback list.
- Message shapes: a spread of lengths (1-word to ~60-word paragraphs), emoji, links (Instagram reels), multi-line messages, stickers/images/videos, a few "edited" markers.

### 6.5 Exhibit A planted story and eval cases
| Planted | Detail |
|---|---|
| The Cindy message | 14 Mar 2025 (Friday), 11:42 PM, Rohan: "cindy from the new team is kinda cute ngl". Tara replies "who is cindy" **4 seconds** later. |
| Cindy mentions | **14 total**: the original, Tara's 4-second reply, and 12 later messages. 11 are spelled "cindy" (any case) and 3 are variants ("cindyy", "sindy", "cindi"). Tara sends 9, Rohan 5. "Mentions since" the original is therefore 13. |
| Paraphrase set | 6 messages calling other people "pretty", "adorable", "good looking", with no literal "cute" (for semantic search). The literal word "cute" also appears in a few other messages (compliments to Tara, a puppy video), so a keyword search for `cute` is deliberately not the same as the semantic set. |
| Hinglish set | 5 spelling variants of "khana khaya?" (khana / khaana / khaya / kha liya) |
| Parser edges | Multi-line messages (23), system lines (encryption notice, number change), `image omitted`/`audio omitted`/`sticker omitted`, deleted markers, `U+200E` before media lines, `U+202F` before AM/PM, a lone `<This message was edited>` |

`eval/queries.jsonl` (≈ 30 queries) uses a sidecar `demo_chat.truth.json` written by the generator, mapping each planted fact to message IDs, so tests and evaluation never hard-code line numbers.

| Query | Expected | What it tests |
|---|---|---|
| `cindy` | 11 exact hits | exact keyword |
| `cindy` (fuzzy on) | all 14 | trigram fuzzy expansion |
| `sindy` | all 14 | typo as query |
| `cute` | Cindy message + the paraphrase set | keyword vs semantic gap |
| `khana khaya` | all 5 variants | Hinglish spelling variance |
| `who said sorry first after 2 aug` | Rohan's 9 Aug "hey" context | filters + date range (added with M7; the sidecar has the first six queries today) |

### 6.6 Sensitivity tests (the stats must not be an artifact of our constants)
Re-run the demo with `CONV_GAP` ∈ {2 h, 4 h, 6 h} and assert, for each: initiator winner = Rohan; reply winner = Rohan (faster) with ratio ≥ 5; `peak_hour` = 2; `longest_streak` = 183; `silence_breaker` = 4 of 4; archetypes = Double Texter / Ghost. Exact medians may move; verdicts must not flip. Implemented in `core/tests/test_stats_demo.py` (`test_verdicts_survive_a_different_conversation_gap`, at 2 h and 6 h, Spicy on) plus the generator-side check in `test_demo_chat.py`. **It found a real problem:** at 2 h Tara stopped being The Ghost, because the archetype scores differed by 0.04. §3.5 now ranks strong fits by editorial priority.

### 6.7 How the generator works (`tools/make_demo_chat.py`, package `tools/demo_chat/`)
Deterministic from a seed (its own RNG built only on `random()`, so the bytes do not change across Python versions). Standard library only. In order:
1. **Scenes** (`scenes.py`): every planted event at a fixed timestamp: the first chat, the first "I love you", the 31-message monologue, the 1,204-message fight, the six silent days and the returns, three more silences, three days on which Tara sends nothing, and the Cindy night. Scene messages are protected from every later stage.
2. **Free conversations** (`convs.py`): three classes per chat day (morning, afternoon, late night), placed so conversations are always more than 4 h apart, which makes the parser's conversations the generator's. Turn lengths, reply delays (Rohan: lognormal, median ≈ 100 s; Tara: a mixture of quick and "busy" replies), double-text gaps, and a **tempo curve** that makes late-night conversations densest in the middle, which is what puts the peak hour at 2 AM.
3. **One RNG stream per chat day.** With a single stream, tuning was chaotic: rounding a knob to the fourth decimal moved the total by 4%. Per-day streams make a knob only perturb the days it touches.
4. **Calibration:** the timing knobs in `params.py` were fitted by random search to the banded targets and then frozen. They are tuned for seed 1234 only; another seed raises a clear error if its volume is off by more than 900 messages, and shows plausible but different banded numbers when it works.
5. **Structure fixes** (`structure.py`): both people send on every active day, message 10,000 is turned into "wait what", and the per-person totals are made exact using only messages after 12 Sep 2024, so earlier positions never move.
6. **Text** (`texts.py`): roles with exact counts (media, deleted, `ok.`, apologies, "who is", links, multi-line, greetings, seed phrases), inline signature words, and budgeted 😭 / "babu" / mild swearing. Each budget is "target minus what the scenes already hold" and is asserted exactly at the end of the build.
7. **Render** (`render.py`): the iOS file with its quirks, plus the truth sidecar.
8. **Verification** (`facts.py`): measures the parsed chat from the definitions in §1.0 and shares no code with the generator.

**Limits (honest):** only the scenes and the planted messages are hand-written. The filler is composed from phrase pools: replies to a question get an answer-shaped reply and openers look like openers, but otherwise neighbouring messages are unrelated. It is good enough for every number, the word clouds and the search tests, and it is not a chat you would enjoy reading. Improving it (for example an offline, committed LLM-written pass) is possible later because the output is committed anyway.

---

## 7. A full example roll (demo couple, seed 1234)

### 7.1 Spicy off
| Slot | Value | Stat | Notes |
|---|---|---|---|
| Top critic ★★★★★ | "It took 47 days for someone to say 'I love you'. It was Tara. Plot twist." — Their Group Chat | `first_ily` | F |
| Laurel | WINNER · LONGEST STREAK · 183 DAYS | `longest_streak` | F |
| Title | 2 AM AND STILL TYPING | `peak_hour` | N |
| Tagline | 47,382 messages. 659 days. Zero chill. | `messages_total`, `span_days` | N |
| Critic ★★★★☆ | "Rohan once sent 31 messages in a row. Tara replied 'hmm'." — The Neighbours | `longest_monologue` | subject Rohan, N |
| Critic ★★☆☆☆ | "Rohan replies in 1m 40s. Tara replies in 23 min. Tara is 'busy.'" — Rohan's Thumbs | `reply_median` | subject Tara, U (her only U) |
| Billing | ROHAN as THE DOUBLE TEXTER · TARA as THE GHOST | archetypes | one U (Ghost), one N |
| Release | IN CHATS SINCE 3 JAN 2024 | `first_message` | |
| Runtime | 131 HRS (OF TYPING) | `runtime_typing` | |
| Rating | [PG] for 2,341 😭, excessive use of "babu" and 38 passive-aggressive "ok."s | `swearing`, `emoji_top`, `pet_name`, `ok_period` | |
| Fine print | BASED ON A TRUE STORY. 47,382 OF THEM. · No chats were stored in the making of this poster. | | |

(Sources and star counts are seeded picks, so a reroll changes them; this is one roll. In the shipped output the top critic's source is "The First Message" and the reply-speed critic's is "Tara's Notification Tray".)

Why this passes the fairness rule (§4.3): Tara has one U line (reply speed) and Rohan has none, because the monologue is N. The billing block has one U archetype (Ghost) and one N (Double Texter), so the "both U" swap in §3.5 does not trigger.

### 7.2 Spicy on (differences only)
- Title: **SORRY 214** (`apologies`, ratio 214:9, above 5×). The apology stat is spent on the title, so it is not also a critic.
- The two critics are unchanged, but the reply-speed line drops to ★☆☆☆☆ (Spicy unflattering lines get one star).
- Rating: **PG-13** for "excessive use of "babu", 38 passive-aggressive "ok."s, 214 apologies and mild emotional damage."
- Billing: unchanged (Double Texter / Ghost): both fit strongly and the Ghost is funnier.
- Director's Cut adds: Clingy-meter (Rohan 84 · Tara 16, "Level: Notification Enthusiast" / "Level: Phone Face-Down"), `bang_then_silence` ("2 Aug 2024: 1,204 messages. Then 6 days of silence. We have questions."), `silence_breaker` (4 of 4), `who_is_that`, `triple_texts`, `fight_days`.

---

## 8. Open questions

1. **Meter naming.** "Love-o-meter" matches your original idea but invites the literal reading. Alternative: "Effort-o-Meter". Recommendation: keep Love-o-meter in the UI with the "text effort" subtitle and the honesty expander.
2. **Lexicons for languages other than English and Hinglish.** The structure supports them; shipping them is out of v1.
3. **Apology and ping lexicons are the most likely to misfire** (sarcasm, quoting). The Director's Cut shows the matched messages on request ("Show me") so users can see what was counted.
4. **`makes_laugh` window (2 min)** is a guess. Tune on real samples in Spike 0.
5. **Book word counts.** Verify in Spike 0 and note the edition.
6. **Lowercase third-party names** are not detected (§5.5, known limit).
7. **Analysis time in the browser is unmeasured.** `analyze()` takes about 1.1 s (1.3 s with Spicy) for 47k messages on CPython 3.13. Pyodide is slower; Spike 0 must time it.
6. **Is `anniversary` worth building?** Cheap, but only matters for chats over a year long. P2, so no decision needed yet.
