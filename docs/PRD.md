# Love Language Model — PRD

> Working title. It's a pun: this is not an LLM. It just counts things, very judgmentally.
> Other options: **Typing…**, **Chatopsy**, **Seen at 2 AM**.

| | |
|---|---|
| Status | Draft v0.1 |
| Date | 21 Nov 2026 |
| Goal | Portfolio project: learn, then show off |
| Companion doc | [STATS.md](STATS.md): every stat, its math, its jokes, and the demo couple |

---

## 1. The pitch

Upload a WhatsApp chat export and a photo. Get back a **movie poster of your relationship**: title, tagline, critic reviews, cast list and age rating, all written from your real chat stats. The Python runs in your browser, so your chat never leaves the tab, and you can check that yourself.

A second tab, **Exhibit A**, searches your whole chat history for receipts ("when did he say Cindy was cute?"). It returns the exact messages with timestamps and context, and turns a result into a courtroom-style evidence card.

## 2. Honest positioning

- Chat analyzers are common (GitHub repos, websites). Message counts and emoji charts alone are not a portfolio piece.
- What sets this one apart, most important first:
  1. **The writing.** Stats become jokes inside a movie-poster format. This is what makes a recruiter smirk.
  2. **Privacy you can check.** Python runs through WebAssembly with no backend: *"Open DevTools → Network, upload your chat, watch nothing leave."*
  3. **Engineering underneath.** Format auto-detection, property-based parser tests, a stat-ranking algorithm, hybrid search with a measured eval.
  4. **Exhibit A.** Fun, and it shows retrieval skills.
- This is not a product: no accounts, no monetization, no growth plan. If it ever gets real users, revisit privacy, consent and abuse before anything else.

### 2.1 What building it teaches

| Area | Where it shows up |
|---|---|
| Regex and messy-data parsing | Export formats, locales, Unicode quirks (§11) |
| Algorithms | Date-order resolution, archetype assignment, stat selection |
| NLP basics | Normalization, lexicons, log-odds word scoring, BM25, embeddings |
| Testing | pytest fixtures, Hypothesis property tests, golden tests, Playwright E2E |
| Web | Pyodide in a Web Worker, DOM-to-PNG export, Web Share API |
| Evaluation | recall@5 for search, measured before and after |

## 3. Principles

1. **Funny beats complete.** Five great lines beat forty stats. Cut any stat that can't produce a good line.
2. **Never invent a quote.** Every message shown anywhere is rendered from the parsed chat by message ID. Generated text never appears inside quote marks.
3. **Private by design, and checkable.** No server ever receives chat content or photos, and users can confirm it.
4. **10-second recruiter path.** Link → demo poster in ≤ 10 s, with no upload.
5. **The Python core is the product; the web is the stage.** The core knows nothing about the UI: bytes in, JSON out.
6. **Punch at behaviors, not people.** Joke about double texts and 2 AM habits. Never about looks, money, family, or whether someone is loved.

## 4. Audiences

| Who | Device | What they need |
|---|---|---|
| Couple (user) | Mostly phone | Easy export steps, a laugh, a card for their story |
| Recruiter (audience) | Desktop, ~30 s | One-click demo, no upload, instantly funny |
| Engineer reviewer | Desktop + GitHub | README that explains the clever parts, tests, clean core, privacy they can verify |

## 5. Scope

**v1 (ship this)**
- WhatsApp exports only (.txt or .zip; iOS and Android; several locales and date formats)
- Exactly two participants
- Poster: one template, 9:16, optional photo
- Director's Cut page: every stat, a few charts, and the **Dueling Clouds** word cloud (each person's distinctive words, not raw frequency; STATS.md §2)
- Spicy mode toggle, reroll jokes, hide any line
- Demo couple (synthetic chat)
- Exhibit A: keyword + fuzzy search, context view, mention timeline, evidence card

**v2**
- Exhibit A semantic search (in-browser embeddings), hybrid ranking, eval numbers
- Offline mode via service worker ("works in airplane mode")
- Second poster template (receipt) and a 4:5 feed format
- Word-cloud share card (heart-shaped mask, 9:16, same export path as the poster)

**v3 / stretch**
- Optional in-browser LLM "Judge's summary" with verified citations (§9.6)
- Telegram / Instagram parsers
- Self-hosted Pyodide and model weights (zero third-party requests)

**Never (non-goals)**
- Server, database, accounts, analytics on chat content
- Group chats
- Media analysis (photos, voice notes)
- Relationship advice or "compatibility" claims

## 6. User flow

1. **Landing.** A sample poster animates in. Two buttons: **Upload your chat** · **See a demo couple**. A small link: *Recruiter? Skip the chat, see the demo →* (runs the demo and opens a "How it's built" panel). Privacy line: *Your chat never leaves this tab. Don't trust us: open DevTools → Network and watch.*
2. **How to export.** Collapsible steps for Android and iOS, stressing **Without media**.
3. **Upload.** Drag and drop or pick a file (.txt or .zip). Consent checkbox: *☐ My partner knows I'm doing this (or will find out from the poster).*
4. **Who's who.** Shows the two detected names. Users can rename them (nicknames appear on the poster) and swap the order. If the date format is ambiguous (§11.3), ask once: *"Is 03/04/24 the 3rd of April or March 4th?"*
5. **Settings.** Spicy mode (off by default). Message quotes (on by default; each one can still be hidden).
6. **Processing.** The browser tab title changes to `typing…`. Rotating lines: *Counting your "ok."s… · Measuring who's clingier… · Consulting the stars (about as scientific as this)…*
7. **Poster.** Add a photo (optional; there's a designed no-photo fallback), crop it, then reroll, hide or swap lines. Export as PNG or share.
8. **Director's Cut.** Every stat that passed its threshold, with charts and the word clouds (tap a word to redact it).
9. **Exhibit A.** The search tab (§9).
10. **🔥 Burn everything.** Clears memory and reloads, showing the "close the tab and it's gone" promise.

Error states, in the app's voice:
- Fewer than 300 messages: *"This isn't a movie, it's a trailer. Come back with more messages."*
- More than two participants: *"6 people? That's not a couple, that's a cast. Group chats aren't supported."*
- Unrecognized format: *"We couldn't read this file. If it's a WhatsApp export, tell us. The anonymizer can make a safe sample."*

## 7. The Poster (main feature)

### 7.1 Why a movie poster and not Wrapped-style slides
- One image with a fixed layout matches "upload a photo, get a card."
- A poster comes with comedy slots built in: title, tagline, critic quotes, cast list, age rating, release date, runtime, festival laurels. Each slot maps to a type of stat, so templating stays clean.
- Critic quotes from absurd sources ("— Their Phone Battery") turn any stat into a joke.

### 7.2 Anatomy

Examples are the demo couple's roll with Spicy off, seed 1234 (full table in STATS.md §7). The shipped demo chat is built to produce exactly these numbers (STATS.md §6).

| Slot | Filled from | Example |
|---|---|---|
| Photo | User upload, full bleed, grain + duotone + vignette | — |
| Top critic | Best wholesome stat | ★★★★★ "It took 47 days for someone to say 'I love you'. It was Tara. Plot twist." — Their Group Chat |
| Laurel | One award-style stat | WINNER · LONGEST STREAK · 183 DAYS |
| Title | Template for the top title theme | 2 AM AND STILL TYPING |
| Tagline | Top couple-level stat | *47,382 messages. 659 days. Zero chill.* |
| Critic quotes ×2 | Next best stats, each with a different theme | ★★★★☆ "Rohan once sent 31 messages in a row. Tara replied 'hmm'." — The Neighbours |
| Heartbeat line | Messages per month, drawn as an ECG line | (visual) |
| Billing block | One archetype per person | ROHAN as THE DOUBLE TEXTER · TARA as THE GHOST |
| Release | Date of first message | IN CHATS SINCE 3 JAN 2024 |
| Runtime | Estimated typing time | RUNTIME 131 HRS (OF TYPING) |
| Rating box | 2–3 count stats | [PG] for 2,341 😭, excessive use of "babu" and 38 passive-aggressive "ok."s |
| Fine print | Fixed jokes | BASED ON A TRUE STORY. 47,382 OF THEM. · No chats were stored in the making of this poster. |

The same couple with Spicy on could roll a title of **SORRY 214** and a rating of *[PG-13] for 214 apologies, 1,190 double texts and mild emotional damage* (Spicy mode raises the rating one level and adds the suffix; STATS.md §5.6).

### 7.3 Mock (layout only)

```
 ★★★★★ "It took 47 days for someone to say 'I love you'.
        It was Tara. Plot twist."                 — Their Group Chat

 ░░░░░░░░░░░░░░░░░░░ couple photo, full bleed ░░░░░░░░░░░░░░░░░
 ░░░░░░░░░░░░░░░░░ grain · duotone · vignette ░░░░░░░░░░░░░░░░░

          ❦ WINNER · LONGEST STREAK · 183 DAYS ❦

                  2 AM AND STILL TYPING
            47,382 messages. 659 days. Zero chill.

 "Rohan once sent 31 messages in a row.
  Tara replied 'hmm'."                           — The Neighbours
 "Rohan replies in 1m 40s. Tara replies in 23 min.
  Tara is 'busy'."                               — Rohan's Thumbs

     ╱╲__╱╲╱╲____╱╲__╱╲╱╲___   (monthly messages as a heartbeat)

     ROHAN as THE DOUBLE TEXTER   ·   TARA as THE GHOST
     IN CHATS SINCE 3 JAN 2024   ·   RUNTIME 131 HRS (OF TYPING)
     [PG] for 2,341 😭, excessive use of "babu"
          and 38 passive-aggressive "ok."s
     BASED ON A TRUE STORY. 47,382 OF THEM.
```

### 7.4 Design direction
- Export at 1080×1920 (Instagram story). A 4:5 feed version comes in v2.
- Fonts, self-hosted and OFL-licensed: a tall condensed display face for the title and billing block (e.g., Bebas Neue, League Gothic, Antonio), a serif for critic quotes (e.g., DM Serif Display), a plain sans for fine print.
- Photo treatment: duotone, film grain, vignette.
  - **Risk (resolved by drawing on a canvas, decision D36):** DOM-to-image libraries can render CSS filters and blend modes badly in iOS Safari.
  - **Fallback:** apply the photo effects with a canvas *before* composing, so the exported DOM only contains a plain image.
- No-photo fallback: gradient + silhouette design, so skipping the photo still looks deliberate.
- No real logos: no WhatsApp logo, no MPA rating logo, no studio marks. The rating box is a generic bordered box. Mentioning names in jokes is fine; using logos isn't.

### 7.5 Controls
- **Reroll 🎲:** new joke variants and tie-breaks, same stats. Seeded RNG, so a given roll is reproducible.
- **Hide line:** replaces it with a black `[REDACTED]` bar. Funny and good for privacy.
- **Swap:** tap a critic quote to pick from the next five best stats.
- **Spicy mode:** adds the desperation, apology and fight stats (STATS.md §1.8).
- **Export (built in M5):** the poster is drawn on a canvas and exported with `canvas.toBlob` as a 1080×1920 PNG (decision D36). "Share…" uses the Web Share API with files where supported; "Download PNG" and "Open image" (long-press to save) cover everything else.
- **Built in M5:** photo (pick, drag/zoom, duotone, grain, vignette), the silhouette design when there is no photo, hide-line (black `[REDACTED]` bar), swap-critic, reroll. Not yet: the 4:5 feed format and a second template (v2).

## 8. Director's Cut

Every stat that passed its threshold, grouped by category. Each shows its line, plus a small chart where useful:
- Heartbeat: messages per month per person (stacked area)
- Hour × weekday heatmap
- Reply-time distribution per person (log scale)
- Top emoji per person
- **Dueling Clouds** (see §8.1)
- Love-o-meter and Clingy-meter, each with a *"How we calculated this (badly)"* expander showing the exact formula. Being open about the math is part of the joke and part of the engineering story.
- Combo lines (STATS.md §1.7), e.g. *"2 Aug 2024: 1,204 messages. Then 6 days of silence. We have questions."*

### 8.1 Dueling Clouds

- **What:** two word clouds, one per person, made of the words that person uses **more than their partner**, not raw frequency. A plain frequency cloud is "I / you / haha" and tells nobody anything.
- **How:** Fightin' Words log-odds with an informative prior, computed in Python (STATS.md §2.2); JS only draws it (`d3-cloud` or `wordcloud2.js`, picked in M0) on a canvas, seeded so a reroll is reproducible.
- **Two modes:** *Dueling* (his words vs her words; the funny one) and *Shared* (the words you both lean on; the sweet one). Same table, almost free.
- **Privacy and safety:** stopwords removed, probable third-party names hidden by default ("Show names" toggle), tap any word to redact it, and nothing is stored.
- **Placement:** Director's Cut in v1; a heart-masked 9:16 share card in v2. Not on the poster (decision D4).
- **Honest note:** this is a good chart, not a headline feature. It stays small so that the poster ships first.

## 9. Exhibit A (the "receipts" tab)

### 9.1 Honest take
- The fun is real and it fits the theme. A courtroom card holding the actual message is very shareable.
- **WhatsApp already has keyword search.** Exhibit A needs to offer more: fuzzy matching, search by meaning ("cute" also finds "pretty"), surrounding context, a mention timeline, "who said it first", and the evidence card.
- **"Single source of truth" and LLM-generated answers contradict each other.** An LLM can paraphrase or invent a quote, and a fake receipt in a fight is the worst possible failure. So v1–v2 is **retrieval only**: the R in RAG, with no G on purpose. Every result is a real message with its real timestamp. Explaining this choice is a good interview moment.
- This is the feature most likely to turn sour. Frame it as comedy, include a disclaimer, and always show the context around a match.

### 9.2 Features

| Feature | Version | Notes |
|---|---|---|
| Keyword search, BM25 ranking | v1 | Message-level index built in Python |
| Fuzzy matching | v1 | Expands query words to similar vocabulary words using character trigrams ("cindy" → "cindyy", "sindy") |
| Filters | v1 | Speaker, date range |
| Context view | v1 | ±5 messages around each hit, match highlighted |
| Mention timeline | v1 | Monthly histogram of matches: *"Cindy: 14 mentions. First: Mar 2025."* |
| Who said it first | v1 | Earliest match and its sender |
| Evidence card | v1 | Exportable PNG (§9.4) |
| Semantic search | v2 | In-browser embeddings, hybrid ranking with RRF |
| Judge's summary | v3 | Optional in-browser LLM, citations verified (§9.6) |

### 9.3 Retrieval design

```
query ─► normalize ─► drop stopwords ─► fuzzy-expand ─► BM25 over messages ─────────────┐
   └───► embed (transformers.js) ─► cosine top-k over conversation windows             │
                                     └─► rank the messages inside those windows ───────┤
                                                                                       ▼
                                                      Reciprocal Rank Fusion (k = 60) ─► message IDs
```

- **Windows.** To keep embedding fast, embed conversation windows (about 6 consecutive messages, stride 3, never crossing a conversation boundary) instead of single messages. Then rank the individual messages inside the top windows.
- **Lazy.** Semantic indexing starts only when the user opens Exhibit A, runs in its own worker, and shows a progress bar. Keyword search works right away.
- **Model.** Start with a small English sentence-embedding model via transformers.js (e.g., `all-MiniLM-L6-v2`, roughly 20–25 MB quantized; verify). Test it on Hinglish. Romanized Hinglish will be weak with any off-the-shelf model, which is why keyword + fuzzy stays in the hybrid ranking.
- **Privacy.** The model weights get downloaded once; chat text never leaves the device.
- **No vector database.** Window embeddings live in one in-memory typed array (`Float32Array`, optionally int8-quantized), searched by brute-force cosine similarity (a dot product against every row; vectors are normalized once). At ~17k windows (a 50k-message chat) that is ~6.4M multiply-adds per query; at the 300k-message cap it is ~38M. An ANN index (HNSW etc.) would add code and bugs for no gain at this size. Nothing is persisted: closing the tab drops the index. Optional, off by default: cache the vectors in IndexedDB so reopening is instant; it stores chat-derived data on the device, so the UI must say so and offer "clear".

### 9.4 Evidence card

```
 EXHIBIT A                                    CASE NO. 2025-CINDY
 THE PEOPLE vs. ROHAN

 14 Mar 2025, 11:42 PM
 Rohan: "cindy from the new team is kinda cute ngl"

 CONTEXT: Tara replied "who is cindy" 4 seconds later.
 MENTIONS OF "CINDY" SINCE: 13

 This exhibit shows what was typed, not what was meant.
 Sarcasm exists. The court is adjourned.
```

The match and its context are rendered from the source by message ID. The quote is never retyped or generated.

### 9.5 Evaluation (the part that impresses engineers)
- The demo chat contains planted test cases: exact matches, typos, paraphrases ("pretty" for "cute") and Hinglish (STATS.md §6).
- `eval/queries.jsonl`: about 30 queries, each with its expected message IDs.
- Report **recall@5** for keyword-only and for hybrid search, and put both numbers in the README (*"hybrid search raised recall@5 from X to Y"*). A measured improvement beats saying "uses RAG."

### 9.6 v3: Judge's summary (optional, clearly labeled)
- An in-browser LLM (WebGPU, desktop only, large download, explicit opt-in) writes a 2–3 sentence summary of the top results and must cite message IDs.
- A validator drops any sentence that cites IDs outside the retrieved set, and any quoted span that isn't a verbatim substring of the cited message.
- Label: *"AI summary — may be wrong. The receipts below are real."*
- The project is complete without this.

## 10. Architecture

### 10.1 Decision D1: UI shell, custom front end (recommended) or stlite

You said stlite (Streamlit running on Pyodide) plus an HTML/JS card sounds good. I recommend a custom front end instead:

| | stlite | Custom HTML/JS + Pyodide worker |
|---|---|---|
| Share of code in Python | Higher | Lower (core only) |
| First load | Heavier: Pyodide + Streamlit and its dependencies | Lighter: Pyodide + one small wheel |
| Look | The default Streamlit look recruiters have seen many times | Fully custom, matching the movie theme |
| Poster | Lives in an iframe component | Plain DOM |
| Exhibit A embeddings (JS) | Awkward to connect | Simple: another worker |
| Mobile layout and animation | Limited | Full control |

Either way, the **core package is identical** (bytes in, JSON out). The choice only affects `web/`. Decide before M4.

### 10.2 Diagram (custom front end)

```
┌──────────────── Browser tab (nothing leaves it) ─────────────────┐
│ main thread: UI, poster DOM, PNG export                          │
│   │ postMessage (file ArrayBuffer is transferred, not copied)    │
│   ├─► py.worker    : Pyodide + lovelm wheel                      │
│   │                  parse → stats → select → poster JSON → BM25 │
│   └─► embed.worker : transformers.js (lazy, Exhibit A only)      │
└──────────────────────────────────────────────────────────────────┘
Static hosting (GitHub Pages / Cloudflare Pages): HTML, JS, wheel, fonts, demo chat
Pinned CDN: Pyodide runtime, model weights. Code and weights only, never user data.
```

Running Python in a worker keeps the page responsive while it processes a 100k-message chat.

### 10.3 Repository layout

```
love-language-model/
├─ core/                      # pure Python, stdlib only (+ maybe `emoji`)
│  ├─ lovelm/
│  │  ├─ ingest.py            # bytes → text: zip, BOM, encodings, Unicode cleanup
│  │  ├─ formats.py           # line grammars per export variant
│  │  ├─ detect.py            # format + date-order detection
│  │  ├─ parse.py             # lines → Messages: multiline, system lines, media
│  │  ├─ model.py             # Message, Chat, Turn, Conversation dataclasses
│  │  ├─ context.py           # shared analysis context: conversations, turns, replies, days, streaks, silences
│  │  ├─ text.py              # normalization, tokens, emoji, lexicon matching
│  │  ├─ lexicons/            # phrases.json, stopwords.json, books.json, placeholders.json (editable)
│  │  ├─ stats/               # base.py (registry, scoring) + volume, effort, language, events: one function per stat
│  │  ├─ words.py             # log-odds signature words + cloud data (STATS.md §2)
│  │  ├─ meters.py            # Love-o-meter, Clingy-meter, archetypes
│  │  ├─ copy.py              # joke templates, titles, taglines + the renderer
│  │  ├─ poster.py            # slot selection + poster JSON
│  │  ├─ charts.py            # data for the Director's Cut charts
│  │  ├─ rng.py               # seeded RNG on random() only (stable across Python versions)
│  │  ├─ search.py            # (M7) BM25 + fuzzy expansion
│  │  └─ api.py               # load_chat(bytes), analyze(chat, ...) -> dict, analyze_bytes
│  └─ tests/
├─ web/                       # vanilla JS + Vite (no framework)
│  ├─ index.html, vite.config.js
│  ├─ src/  main.js, engine.js, py.worker.js, glue.py, render.js, privacy.js, errors.js, dom.js, style.css
│  │         (later: poster/, cloud/, exhibit/, embed.worker.js)
│  ├─ scripts/  prepare-assets.mjs (copies Pyodide, builds the wheel, copies the demo), smoke.mjs
│  ├─ test/  errors.test.mjs (node --test)
│  └─ public/  (generated, gitignored) pyodide/, wheels/, demo/, assets.json
├─ tools/
│  ├─ make_demo_chat.py       # deterministic synthetic couple (STATS.md §6); package demo_chat/, output in demo/
│  └─ anonymize_export.py     # turns a real export into a safe format sample
├─ eval/queries.jsonl
└─ docs/  PRD.md, STATS.md
```

**Why stdlib only:** it loads faster in Pyodide, tests natively without setup, and "zero-dependency core" is a good README line. Use pandas in a notebook while exploring if you want to learn it, but keep it out of the shipped core.

### 10.4 Core contract (versioned JSON)

```json
{
  "schema": 1,
  "meta": {"format": "ios", "date_order": "DMY", "has_seconds": true, "range": ["2024-01-03", "2025-10-23"],
           "messages": 47382, "conversations": 1739, "warnings": [], "spicy": false, "quotes": true, "conv_gap_hours": 4},
  "people": {"A": {"name": "Rohan"}, "B": {"name": "Tara"}},
  "stats": [
    {"id": "longest_monologue", "pri": "P0", "kind": "event", "theme": "effort", "valence": "N", "spicy": false,
     "subject": "A", "score": 1.0, "quote_ids": [12397],
     "values": {"n": 31, "W": "Rohan", "L": "Tara", "q": "hmm", "date": "2024-06-14"},
     "lines": ["Rohan once sent 31 messages in a row. Tara replied 'hmm'.", "31 messages in a row, from Rohan. Then silence. Then 'hmm'."]}
  ],
  "poster": {"title": {}, "tagline": "...", "laurel": {}, "top_critic": {}, "critics": [], "billing": [],
             "release": "...", "runtime": "...", "rating": {}, "fine_print": [], "heartbeat": [], "alternatives": []},
  "meters": {"love": {}, "clingy": {}},
  "archetypes": {"A": {}, "B": {}},
  "words": {"dueling": {}, "shared": [], "tokens": {}, "hidden": []},
  "charts": {"heartbeat": {}, "heatmap": {}, "reply_hist": {}, "hours": {}},
  "seed": 1234
}
```

`clingy` exists only in Spicy mode. `analyze(chat, seed, spicy, quotes, names, swap, conv_gap_hours)` is cheap to call again: reroll, the Spicy switch, the quotes switch and nicknames all just call it again (about 1.1 s for 47k messages on CPython; Pyodide is unmeasured). Every stat that passed its threshold is in `stats`, with all its eligible line variants; `poster.alternatives` holds the next-best critic candidates for the "swap" control.

### 10.5 Privacy measures (concrete and checkable)
- No backend. Static files only.
- A CSP meta tag limits `connect-src` to the site itself: Pyodide is self-hosted (D34), so there is no CDN to allow. (v2's embedding model weights would need a deliberate, pinned exception.)
- No analytics in v1. If added later: page views only, never content.
- Files are read with `File.arrayBuffer()` and transferred to the worker. Nothing goes into `localStorage` or IndexedDB except cached model weights (v2), which contain no user data.
- **Automated privacy test (built in M6):** Playwright uploads a chat into the production build and fails on any request that leaves the site, any non-`GET`, any request body or any console error (CSP violations included), and asserts zero requests from "ready" to the finished poster (D42).
- 🔥 Burn button: terminate the workers, revoke object URLs, reload.
- **Live readout (built in M4):** a footer line and the "How it's built" tab report the network requests made since the chat was in memory (0 in a real run), and list every file loaded before it (all same-origin). The engine is fully started before the file is read, so this is true regardless of timing (decision D33).
- **Strict CSP in production (built in M4):** `default-src 'none'; script-src 'self' 'wasm-unsafe-eval'; connect-src 'self'; ...`; the page uses no inline styles or `innerHTML`.

## 11. Parsing spec (expect this to be a big chunk of the work)

### 11.1 Inputs
- Android usually exports a `.txt`; iOS usually exports a `.zip` containing `_chat.txt` (verify in Spike 0). Handle both with Python's `zipfile`.
- Decode with `utf-8-sig` (strips the BOM); fall back to UTF-16 if detected.
- Unicode cleanup: remove `‎` / `‏` (direction marks iOS inserts), turn ` ` and ` ` (narrow and no-break spaces before AM/PM) into plain spaces, normalize to NFC.

### 11.2 Line grammars (starting set; extend from real samples)

| Variant | Example header |
|---|---|
| Android 12h | `31/12/24, 11:59 pm - Rohan: text` |
| Android 24h | `31/12/2024, 23:59 - Rohan: text` |
| iOS | `[31/12/24, 11:59:58 PM] Rohan: text` |
| US date order | `12/31/24, 11:59 PM - Rohan: text` |
| Dotted dates | `31.12.24, 23:59 - Rohan: text` |

- A line that doesn't match a header pattern continues the previous message (multiline messages).
- A header with no `Name: ` part is a system line (encryption notice, number change, etc.).
- Detection: take the grammar of the first header found in the first 10 non-empty lines; if there is none, show the "unrecognized format" error. The share of lines that are headers is reported as a warning, never a gate (multi-line messages dilute it; see decision.md D14).

### 11.3 Date-order resolution (a good algorithm to talk about)
1. If any first date field is > 12, dates are day-first. If any second field is > 12, they're month-first.
2. If still ambiguous (every date has both fields ≤ 12), parse both ways and count *time-order violations* between consecutive messages. The correct order has close to zero. Pick the lower count.
3. If that's a tie too, ask the user once (§6, step 4).
4. Two-digit years: add 2000.

### 11.4 Message kinds
`text`, `media`, `deleted`, `system`, `call` (if present), plus an `edited` flag. Placeholder strings for media and deleted messages vary by platform and phone language, so keep them in `lexicons/placeholders.json` (e.g., `<Media omitted>` on Android; `image omitted`, `sticker omitted`, `audio omitted` on iOS; `This message was deleted`; `You deleted this message`; `<This message was edited>`).

**Android uses one placeholder for all media**, so voice-note and sticker stats work on iOS only. Each stat checks what data is available and skips itself if it can't run.

### 11.5 Participants
- Count distinct senders on non-system lines. If it isn't exactly 2, reject with the "cast" joke (§6).
- Names are whatever the exporting phone had saved ("Babu ❤️", or a phone number). The *Who's who* step fixes this.

### 11.6 Timestamp caveats
- Every timestamp is in the exporting phone's local time. Long-distance couples get misleading night stats. (Stretch: a "we're long distance" setting with a timezone offset per person.)
- Android stores **minutes only**. A reply under 60 s shows as 0, so display "under a minute", never "0 min".
- Daylight-saving changes can create negative gaps. Clamp them to 0 and keep file order.

## 12. Stats engine (summary; full detail in STATS.md)

- Building blocks: **turn** (a run of messages from one sender), **conversation** (a gap of ≥ 4 h starts a new one), **chat day** (ends at 5 AM, not midnight, because couples don't sleep at midnight).
- Each stat returns its `values`, a `score` from 0 to 1 for how interesting it is, flags (`spicy`, `quote_ids`), and copy lines.
- Each stat has a minimum sample size and skips itself below it.
- Selection fills the poster slots greedily, uses each theme at most once, and always includes at least one wholesome line.
- Love-o-meter and Clingy-meter are simple formulas, fully disclosed in the UI.
- Word analysis (signature words and both cloud modes) is one log-odds table computed once in Python; JS only lays it out (STATS.md §2).

## 13. Testing strategy

| Layer | What | Tooling |
|---|---|---|
| Parser fixtures | One fixture per format variant and quirk (direction marks, ` `, multiline, system lines, localized placeholders) | pytest |
| Round-trip property tests | Generate random chats → write them in every export format → parse → must equal the original | Hypothesis |
| Date order | Ambiguous dates, DST jumps, 2-digit years | pytest |
| Stats golden tests | Demo chat has planted values (STATS.md §6); every stat is checked against them | pytest |
| Word analysis | Log-odds on a toy corpus equals a hand-computed value; stopword and third-party-name filters; demo signature seeds appear in each person's top 5 (≥ 4 of 5) | pytest |
| Sensitivity | Changing the conversation gap from 2 h to 6 h must not flip any "who" stat on the demo | pytest |
| Pyodide smoke test | The exact browser path (Pyodide + the wheel + `glue.py`) runs in Node and its JSON equals native CPython's (built, `npm run smoke`) | Node + Pyodide |
| E2E | Demo → poster → PNG export; privacy network assertion on the production build (built, 9 tests, D42) | Playwright in the installed Chrome |
| Retrieval eval | recall@5, keyword vs hybrid | `eval/run.py` |

CI: GitHub Actions runs all of these on every push (`.github/workflows/ci.yml`, written but never run: D43).

## 14. Performance budgets (targets; measure, then adjust)

| Metric | Target |
|---|---|
| Cold load → demo poster (desktop, broadband) | ≤ 10 s; start loading Pyodide when the page opens |
| Warm load → demo poster | ≤ 3 s |
| Analyze 100k messages (desktop) | ≤ 5 s |
| Largest supported chat | 300k messages (warn above that) |
| Poster PNG export | ≤ 2 s |
| *Measured (M4):* start Python / read 47k messages / analyze 47k messages | 0.7 to 0.9 s / 0.6 to 0.9 s / 2.0 to 2.1 s in a browser (decision D31) |
| Word cloud layout (40 words per side) | ≤ 1 s |
| Semantic index for 50k messages (desktop, WASM) | ≤ 2 min with a progress bar; keyword search available immediately |

## 15. Touches that make recruiters smirk

- *Recruiter? Skip the chat →* link on the landing page.
- A console easter egg for anyone who opens DevTools: *"Checking the Network tab? Good. Nothing's leaving. Also, the person who built this is open to work → [link]"*
- The browser tab title shows `typing…` while processing.
- 404 page: **"Left on read."**
- Footer: *No chats were stored in the making of this poster.*
- The "signature words" stat and the word clouds use a real NLP method literally named **Fightin' Words** (Monroe, Colaresi & Quinn, 2008). Mention it in the README.
- Hovering a word in the cloud says: *"Rohan said this 405 times. Tara said it 7 times."*
- The 🔥 Burn button.
- A README section, "Verify the privacy yourself", in three steps.

## 16. Milestones

| # | Milestone | Done when |
|---|---|---|
| M0 | Spike 0 (§18) | Real export samples collected through the anonymizer; Pyodide-in-worker hello world; DOM-to-PNG tested on iOS Safari |
| M1 | Parser | All fixtures and Hypothesis round-trip tests pass; format and date order detected |
| M2 | Demo chat generator | `make_demo_chat.py` deterministically produces the planted demo |
| M3 | Stats, selection, copy | Every P0 stat passes its golden test; the poster JSON is funny when read aloud |
| M4 | Web shell | Upload → Who's who → poster JSON on screen; demo button works; Pyodide runs in a worker |
| M5 | Poster | Designed poster, photo crop, reroll/hide/swap, PNG export and share on iOS and Android |
| M6 | Ship v1 | Deployed, README with GIF, privacy E2E test passing, Director's Cut including Dueling Clouds |
| M7 | Exhibit A v1 | Keyword + fuzzy search, context, timeline, evidence card |
| M8 | Exhibit A v2 | Embeddings + RRF, recall@5 numbers in the README |

Ship M6 before starting M7. A finished poster beats an unfinished poster plus half a search tab.

**Status (23 Nov 2026).** M1 to M6 are built, and the screens were then redesigned for simplicity (decision D45): the Poster, Director's Cut and Dueling Clouds sections above describe the earlier version. M6's "Deployed" is *ready but not done*: the CI and Pages workflow, `_headers`, 404 page and licences exist (D43), but there is no repository or remote yet, so nothing has been published and the workflow has never run. M0's remaining parts are still open: real export samples (the anonymizer for them exists, D44), iOS Safari (D40) and real-device speed.

## 17. Risks

| Risk | Mitigation |
|---|---|
| Format variety breaks parsing | Anonymizer tool, samples from friends, strict detection with a clear error |
| Jokes hurt instead of amuse | Spicy off by default; hide/reroll on every line; "behaviors, not people" rule; meters are openly silly |
| A private quote ends up on a shared poster | Quotes capped at 6 words; global quotes toggle; every quote hideable |
| One partner uploads without the other knowing | Consent checkbox (playful but present); nothing leaves the device anyway |
| Exhibit A used to start real fights | Context always shown, disclaimer, no generated quotes |
| iOS Safari export rendering bugs | Pre-render photo effects on canvas; test in M0 |
| Slow on phones | Worker, progress lines, 300k-message cap, semantic search desktop-first |
| Hinglish and code-mixed text | Editable lexicons; keyword + fuzzy always part of search |
| Scope creep ("make it grand") | Milestone order is fixed; v1 is the poster |

## 18. Assumptions to check in Spike 0

1. Current WhatsApp export formats on iOS and Android: container type, header pattern, placeholder strings, and whether call events and edit markers appear.
2. The pinned Pyodide version: its Python version, cold download size, and whether `emoji` installs through micropip (fall back to a regex if not).
3. The poster canvas, fonts and export on iOS Safari (decision D40: still untested, needs full Xcode).
4. Web Share API with files: does sharing straight to Instagram Stories work on iOS and Android?
5. transformers.js embedding speed on a mid-range Android phone and on a laptop; model download size.
6. Constants cited in STATS.md: 36 WPM for "runtime" (Palin et al., MobileHCI 2019, 36.2 WPM, found in a search) and the book word counts (the Philosopher's Stone figure is commonly cited as 76,944; the other four are from memory and still need checking). Confirm both and add the citations to the README.
7. Word-cloud library: pick between `d3-cloud` and `wordcloud2.js` (license, size, emoji rendering on iOS).

## 19. Open decisions

**Resolved in [decision.md](decision.md):** D1 custom HTML/JS shell, D2 name "Love Language Model", D3 quotes on by default, D4 word cloud in Director's Cut (not on the poster). The entries below are kept for the record.

- **D1 — UI shell:** custom front end (recommended) or stlite.
- **D2 — Name:** Love Language Model, Typing…, Chatopsy, or Seen at 2 AM.
- **D3 — Message quotes by default:** on (funnier) or off (safer). Recommendation: on, with the 6-word cap.
- **D4 — Word cloud placement:** Director's Cut in v1 plus a share card in v2 (recommended), or on the poster. Recommendation: not on the poster; it is already full and a cloud competes with the photo.
