# Decision log

Every decision taken for v1, with the reasoning, what was rejected, and what would make us revisit it. Newest decisions go at the bottom of their section; reversed decisions are struck through, never deleted.

Date: 21 Nov 2026 · Status of v1: M1 (parser), M2 (demo chat generator), M3 (stats, poster selection, copy), M4 (web shell), M5 (designed poster) and M6 (browser tests, polish, deploy files, anonymizer; not yet deployed) done, then redesigned for simplicity (D45). Spike 0 was skipped by choice; its Pyodide parts were done inside M4 (see D9, D34). See [PRD.md](PRD.md) and [STATS.md](STATS.md).

## Summary

| ID | Decision | Status |
|---|---|---|
| D1 | UI shell: custom HTML/JS + Pyodide in a Web Worker (not stlite) | Decided |
| D2 | Name: **Love Language Model** (package `lovelm`) | Decided |
| D3 | Message quotes on by default, with the 6-word cap and quote guard | Decided |
| D4 | ~~Word cloud: Director's Cut in v1, share card in v2, never on the poster~~ | Superseded by D45 (no word cloud on screen) |
| D5 | Exhibit A is retrieval-only; no vector DB; LLM summary only as optional v3 | Decided |
| D6 | Core is pure-Python, standard library only, Python ≥ 3.11 | Decided |
| D7 | Core contract: bytes in, versioned JSON out | Decided |
| D8 | Front end: Vite + vanilla JS (ES modules, JSDoc), no framework, no TypeScript in v1 | Decided |
| D9 | Core ships to the browser as a pure-Python wheel, unpacked into Pyodide (no micropip) | Decided, revised in M4 |
| D10 | ~~Poster: HTML/CSS rendered to PNG~~ | Superseded by D36 in M5 |
| D11 | One poster template, 9:16 at 1080×1920, in v1 | Decided |
| D12 | Static hosting, no backend, no analytics in v1 | Decided |
| D13 | Demo chat: deterministic generator, committed output, iOS format | Decided |
| D14 | Parser: format grammars as data, detect by match rate, resolve date order by evidence | Decided |
| D15 | Tests: pytest + Hypothesis; stats use exact, budgeted and banded assertions | Decided |
| D16 | Build order: M1 parser first; poster ships before Exhibit A | Decided |
| D17 | Meters stay in Director's Cut, never on the poster; name stays "Love-o-meter" | Decided |
| D18 | License: MIT | Decided |
| D19 | Version control left to the user; `.gitignore` included, nothing committed | Decided |
| D20 | Fonts: Bebas Neue, DM Serif Display, Inter (all OFL), self-hosted | Decided; installed in M5 with your approval (D37) |
| D21 | Demo generator lives in `tools/demo_chat/`, output in `demo/`, not in the shipped core | Decided (M2) |
| D22 | The generator is calibrated for one seed, with one RNG stream per day | Decided (M2) |
| D23 | Demo facts are verified on the parsed chat by code that shares nothing with the generator | Decided (M2) |
| D24 | Several doc bands were loosened after measuring | Decided (M2) |
| D25 | Filler text is template-composed; only scenes are hand-written | Accepted limitation (M2) |
| D26 | Stats are small registry functions over one shared context; every stat must have copy | Decided (M3) |
| D27 | Poster ranking is editorial: `charm` weights, two-decimal ties, laurel first, countable stats kept out of critics | Decided (M3) |
| D28 | Archetypes: strong fits are decided by editorial priority, not by noise | Decided (M3), found by a test |
| D29 | Variety is seeded: a reroll is a new seed, and any seed reproduces exactly | Decided (M3) |
| D30 | Third-party names: a heuristic guard with explicit limits and manual escape hatches | Accepted limitation (M3) |
| D31 | Analysis speed: measured on CPython, Node+Pyodide and in the browser | Measured (M3, M4); borderline at 100k |
| D32 | Web shell: Vite + vanilla JS, classic worker, no inline styles, strict CSP | Decided (M4) |
| D33 | The privacy readout is true by construction: Python starts before the chat is read | Decided (M4), found by the readout itself |
| D34 | Pyodide 0.29.5 (Python 3.13.2), self-hosted, not the newest 314 line | Decided (M4) |
| D35 | Pyodide must equal native CPython, byte for byte; this found a hash-order bug | Decided (M4) |
| D36 | The poster is drawn on a canvas, not DOM-to-image; one render path for preview and export | Decided (M5), supersedes D10 |
| D37 | Fonts via `@fontsource` 5.3.0 (Latin subsets), loaded before the chat is read | Decided (M5) |
| D38 | The photo is processed on canvases in the tab and never becomes a URL | Decided (M5) |
| D39 | ~~A pure layout engine, so the poster's text layout is tested without a canvas~~ | Superseded by D45 (one-idea poster; its bar geometry is still a tested pure function) |
| D40 | iPhone Safari is untested: this Mac has no full Xcode | Open risk (M5) |
| D41 | ~~Dueling Clouds use our own spiral layout of real `<button>`s, not a cloud library~~ | Superseded by D45 (removed) |
| D42 | Browser tests drive the production build in the installed Chrome; pixel checks measure visible change, not equality | Decided (M6) |
| D43 | Ready to deploy, not deployed: CI and Pages workflow, `_headers`, 404, licences (the workflow has never run) | Decided (M6), open risk |
| D44 | The anonymizer scrambles content, keeps structure, and refuses to write a sample that parses differently | Decided (M6) |
| D45 | Redesign for simplicity, chosen by a three-way design arena: one path, five highlights, a one-idea poster, receipts one level deeper | Decided (after M6), supersedes D4, D39, D41 and the M5 poster |
| D46 | The words live in the front end (`facts.js`); the core sends numbers. The poster's bars are the real messages | Decided (after M6) |

Deferred on purpose: see the last section.

---

## D1. UI shell: custom HTML/JS, not stlite

**Decision.** The web layer is hand-written HTML/CSS/JS. Python runs in a Web Worker through Pyodide. We do not use stlite (Streamlit on Pyodide).

**Why.**
- **Look.** The poster is a designed object. Streamlit's default look is the one recruiters have seen the most; fighting it costs more than building the page.
- **Weight.** stlite downloads Pyodide *plus* Streamlit and its dependencies. A custom shell downloads Pyodide plus one small wheel. The first load is the recruiter's first impression, and the PRD budget is 10 s cold.
- **Poster in the DOM.** Exporting a PNG from a DOM node is simple. Inside a Streamlit component iframe it is awkward.
- **Exhibit A.** The embeddings model (transformers.js) is JavaScript. Wiring a second worker into a custom page is easy; into stlite it's awkward.
- **Mobile.** The users are couples on phones. Layout and animation need full control.
- **Cost is small.** The Python core is identical in both options, so the choice only affects `web/`.

**Rejected.** stlite: higher share of Python in the repo, which is the one real argument for it. We keep that argument honestly: the core *is* the Python showpiece, and it's about 90% of the logic.

**Revisit if.** The shell takes more than ~1 week of M4–M5 work with no working demo.

## D2. Name: Love Language Model

**Decision.** Public name **Love Language Model**. Python package `lovelm`. The README tagline is "Not an LLM. It just counts things, very judgmentally."

**Why.** The pun is the joke and the pitch: a recruiter reads it as "ML project", then smirks when it isn't. It is short enough for a package name, and it's distinct from every other "WhatsApp analyzer". **Rejected:** *Typing…* (hard to search), *Chatopsy* (a bit morbid for a couples app), *Seen at 2 AM* (good, but it describes one stat). The latter can be the poster's catchphrase.

**Revisit if.** The pun gets confusing for non-ML readers. Renaming is a UI string; the package name doesn't need to change.

## D3. Message quotes on by default

**Decision.** Poster quotes are on by default. They're capped at 6 words and pass the quote guard (STATS §5.5: no URLs, numbers, probable third-party names, profanity). Each quote can be hidden, and one toggle removes all of them.

**Why.** Quoted messages ("hmm") are the funniest part of the poster. The guard handles the privacy risk, and nothing leaves the device. **Rejected:** off by default. It makes the poster blander in the one place a recruiter looks first.

## D4. Word cloud placement

**Decision.** "Dueling Clouds" (each person's distinctive words) in the Director's Cut in v1; a share card in v2; never on the poster.

**Why.** The poster is full and the photo needs room. The data is the same table as the signature-words stat, so v1 cost is small. **Rejected:** a plain frequency cloud (STATS §2.1: it says nothing).

## D5. Exhibit A: retrieval only, no vector DB

**Decision.** Exhibit A only retrieves real messages. No generated text is ever shown inside a quote. Semantic search (v2) keeps its vectors in an in-memory typed array and finds neighbours by brute-force cosine similarity. An optional LLM summary is v3, opt-in, with citation validation.

**Why.**
- In a fight, an invented or paraphrased message is the worst possible failure. Retrieval cannot invent.
- A vector DB is for scale, persistence and many users. We have one chat in one tab: about 17k windows for a 50k-message chat, ≈ 6.4M numbers. Brute force is fast enough and adds no library, no bugs and no data leaving the tab.
- Nothing is persisted by default, which is the privacy promise ("close the tab and it's gone").

**Rejected.** An ANN index (HNSW etc.): unnecessary at this size. An always-on LLM answer: hallucination risk plus a large download.

**Revisit if.** Spike 0 shows brute-force search is slow on a mid-range phone at the 300k-message cap. Then quantize to int8 first; only then consider an index.

## D6. Core: pure Python, stdlib only, Python ≥ 3.11

**Decision.** `core/lovelm` uses only the standard library (dataclasses, re, zipfile, statistics, unicodedata, datetime). The minimum Python version is 3.11. No pandas, numpy or NLTK in the shipped core.

**Why.**
- **Pyodide load time.** Every dependency is downloaded by the user's browser.
- **Python version.** The local interpreter is 3.13, but Pyodide ships its own version that may be older. Targeting 3.11 keeps the core runnable on both without surprises. The exact Pyodide pin happens in M0.
- **Testing.** A stdlib-only core runs natively under pytest with no setup.
- **Story.** "Zero-dependency core" is a real README line, and it shows the algorithms are ours.

**Rejected.** pandas: it is the usual tool, and heavy in the browser. Exploration in a notebook with pandas is fine, but it never enters the shipped core.

## D7. Core contract: bytes in, versioned JSON out

**Decision.** `lovelm.api` exposes `analyze(data: bytes, options) -> dict` and (later) `search(...)`. The result is plain JSON-serializable data with a `schema` version. The core knows nothing about the DOM, files, or the browser.

**Why.** The same code is tested natively, run in Pyodide, and could be reused in a CLI. It also keeps the UI decision (D1) cheap to reverse.

## D8. Front end: Vite + vanilla JS

**Decision.** Vite for dev and build, plain ES modules, JSDoc for types. No React/Vue/Svelte. No TypeScript in v1.

**Why.** The UI is about five screens with one heavy part (the poster). A framework would add more than it saves, and recruiters opening the repo should see the interesting code (the Python core), not framework boilerplate. TypeScript is good practice but adds config and friction for a one-person project that already has a typed Python core. **Revisit if** state management gets painful by M5.

## D9. Delivering the core to the browser

**Decision.** Build `lovelm` into a pure-Python wheel at build time (`pip wheel core`, from a clean `build/` so no stale code ships). The worker fetches it from the same origin and unpacks it into Pyodide with `pyodide.unpackArchive(buffer, "wheel")`.

**Why.** The browser runs the exact package that pytest tests (a real import path, no copy-pasted code), and a test checks the wheel is byte-identical to the sources. A pure-Python wheel needs no compilation. **Rejected:** writing files into Pyodide's virtual filesystem by hand (drifts from the tested code).

**Revised in M4 (was: install with micropip).** The npm `pyodide` package ships only the runtime, not `micropip` or any other package, so micropip would have fetched them from a CDN. `unpackArchive` needs nothing else, keeps the site fully self-hosted, and removes a download. `emoji` is not needed: the core uses its own regex.

## D10. Poster rendering (superseded by D36)

> **Superseded in M5.** The poster is drawn directly on a canvas; see D36 for why. The text below is kept as the record of the original plan.

**Decision.** The poster is HTML/CSS. It is exported to PNG with `html-to-image` (fallback: `modern-screenshot`). Photo effects (duotone, grain, vignette) are pre-rendered on a canvas, so the exported DOM contains a plain image.

**Why.** HTML/CSS looks far better than Pillow, and designing it is faster. DOM-to-image libraries can mishandle CSS filters and blend modes in iOS Safari, and pre-rendering removes that risk instead of hoping it doesn't happen.

**Pending.** We have not yet tested export on iOS Safari. M0 must do so before the design is locked (the iOS Simulator is available for this).

## D11. One template, 9:16

**Decision.** One poster template at 1080×1920 for v1. The 4:5 feed format and a second template wait for v2.

**Why.** Instagram stories are where it gets shared. One finished template beats two half-finished ones.

## D12. Static hosting, no backend, no analytics

**Decision.** Static files on GitHub Pages (or equivalent). A Content-Security-Policy meta tag limits network access to the pinned Pyodide and model CDNs. No analytics in v1.

**Why.** It makes the privacy claim checkable (open DevTools → Network). Analytics, even page-view-only, weakens that line for a tiny benefit.

## D13. Demo chat

**Decision.** A deterministic generator (`tools/make_demo_chat.py`) produces the Rohan & Tara chat in iOS format plus a truth sidecar. The output is committed. The generator is tested for determinism.

**Why.** A recruiter will not upload their own chat; the one-click demo is the project's front door. Determinism makes the golden tests stable. **M2 result:** the file is 3.06 MB (0.51 MB gzipped by the host) and builds in about half a second, so the open question is closed: the output stays committed and is not generated in the browser.

## D14. Parser design

**Decision.**
- Two structural header grammars, Android (`31/12/24, 11:59 pm - Name: text`) and iOS (`[31/12/24, 11:59:58 PM] Name: text`), live in `formats.py` as data. Date order, 12/24-hour clock, separators and seconds are *detected from the file*, not enumerated as more grammars. Adding a variant is a fixture plus, at most, a regex tweak.
- Detection: the format is the grammar of the first header found within the first 10 non-empty lines (a real export starts with one; a stray title line is tolerated and skipped). If none, raise "unrecognized format".
  - **Changed during implementation.** The PRD first said to require ≥ 0.9 of sampled lines to be headers. I tried 0.8 next, and Hypothesis immediately produced a valid chat that failed it: multi-line messages legitimately make many lines non-headers. A match-rate gate rejects real chats and does nothing that the later checks (exactly two participants, ≥ 300 messages) don't already do. The rate is still computed and reported as a `low_header_match_rate` warning when it drops below 0.5, so the UI can say "this file looks unusual", but it never blocks.
- Date order: (1) a first field > 12 means day-first, a second field > 12 means month-first; (2) otherwise count time-order violations under each reading and pick the lower; (3) a tie is reported to the UI, which asks the user once.
- A line that doesn't match a header continues the previous message. A header with no `Name: ` part is a system line.
- Media and deleted placeholders live in a data file, not in code.

**Why.** Export formats vary by phone, locale and OS version. Adding a format must be a data change plus a fixture, not a refactor. Evidence-based date-order resolution is more robust than guessing from a locale, which we don't have.

**Rejected.** One giant regex (unreadable, untestable). Guessing from the browser's locale (the exporting phone's locale is what matters, and it isn't known).

## D15. Test strategy

**Decision.** pytest with Hypothesis. Parser: one fixture per format variant, plus round-trip property tests (generate chat → write in every format → parse → equal to original). Stats on the demo: three assertion kinds from STATS §6.3 — **exact**, **budgeted** and **banded** (tolerance). Sensitivity tests (STATS §6.6) guard against results that depend on our constants. Playwright E2E arrives with the web shell.

**Why.** Real-world messy input is the risk, and property tests find edge cases a person won't think of. Banded assertions avoid brittle tests on stochastic data while still catching real regressions.

## D16. Build order

**Decision.** M1 parser → M2 demo generator → M3 stats and copy → M4 web shell → M5 poster → M6 ship. Exhibit A (M7–M8) starts only after M6.

**Why.** A finished poster beats an unfinished poster plus half a search tab. The parser is the riskiest part, so it goes first.

## D17. Meters

**Decision.** Love-o-meter and Clingy-meter live in Director's Cut only, never on the poster. The name "Love-o-meter" stays, with the subtitle "text effort" and the "how we calculated this (badly)" expander. Clingy-meter is Spicy-only.

**Why.** The name is what you wanted and is funnier than "Effort-o-Meter". The subtitle and honesty expander handle the "you can't measure love from texts" problem. Keeping them off the poster means the shared image never carries a verdict on someone's feelings. This resolves STATS §8 item 1.

## D18. License: MIT

**Why.** It's a portfolio project; the permissive license is the default recruiters expect, and nothing in it needs a copyleft guard. The demo chat and fonts must remain compatible (fonts are OFL, D20).

## D19. Version control

**Decision.** I did not run `git init` and will not commit. A `.gitignore` is included (venv, caches, build output). Starting the repository and making commits stays your call.

**Why.** Initializing history and committing are your decisions, not mine.

## D20. Fonts

**Decision.** Bebas Neue (title and billing), DM Serif Display (critic quotes), Inter (small text), all SIL OFL, self-hosted. Until M5 the CSS uses a system-font fallback stack.

**Why.** Poster typography is what makes it look like a movie poster. OFL permits embedding and redistribution. Self-hosting avoids a third-party request that would break the "no requests" privacy test. **Not yet fetched:** the font files are downloaded in M5.

## D21. Where the demo generator lives

**Decision.** The generator is a stdlib-only package, `tools/demo_chat/`, with a thin CLI, `tools/make_demo_chat.py`. Its output is committed to `demo/` (`demo_chat.txt`, `demo_chat.truth.json`). It is **not** part of `core/lovelm`.

**Why.** It builds test data, not product behavior: shipping it in the wheel would make every visitor download code they never run. Tests reach it through `core/tests/conftest.py`. `python3 tools/make_demo_chat.py --check` exits non-zero when the committed files differ from a fresh build, and a test does the same, so the demo cannot silently drift from the code.

## D22. One calibrated seed, one RNG stream per day

**Decision.** The banded facts (reply medians, initiation share, peak hour, double texts) were fitted by random search and frozen for seed 1234. The RNG gives every chat day its own stream. Other seeds are allowed, but raise a clear error if their volume is more than 900 messages off.

**Why.** The first version used one stream through the whole timeline. Tuning then became chaotic: rounding a knob to its fourth decimal changed the total by 4% (47,406 to 45,522 messages) because every later day was reshuffled. Per-day streams make a knob affect only the days it touches, and the search converged. I also checked what other seeds do: seeds 1 and 2 give plausible variants (Tara's median 1,299 s and 1,277 s) and seed 3 cannot balance its totals. So seed 1234 is special, and the docs say so instead of implying the numbers fall out of the method.

**Rejected.** Making the generator self-calibrate for any seed: more code for a demo that needs exactly one realization.

## D23. Independent verification

**Decision.** `tools/demo_chat/facts.py` measures a chat from the definitions in STATS §1.0 and shares no code with the generator. `core/tests/test_demo_chat.py` checks the **parsed** file with it, plus regexes written inside the test.

**Why.** A generator that checks its own bookkeeping proves nothing. I mutation-tested this: changing Tara's "hmm" to "ok", deleting one 😭, delaying the Cindy reply by 5 seconds, deleting one fight-day message and adding a third `ok.` for Rohan were each caught by the specific fact test, not only by the freshness test. The parser reading the whole 47,382-message file with no warnings is also the best end-to-end test M1 has had.

## D24. Doc bands loosened after measuring

**Decision.** Several STATS §6.3 numbers were first guesses made before anything could be measured. Once the generator existed I replaced them with what it produces, and said so in the doc:
- Double texts: guessed 1,312 (±5%); measured 1,190 (Rohan 1,067, Tara 123). Band is now 1,100–1,300 with Rohan > 7× Tara.
- Peak hour: guessed "next-best hour ≤ 7.5%"; measured 3 AM at 7.5% with 2 AM at 10.5%. The real property is "a clear winner", so the band is a lead of at least 1.5 points.
- Initiation: guessed 71% ±3; measured 69.2%, band 68–74%.
- The Cindy count: the doc said "the original + 13 later" while also counting Tara's reply, which would be 15. The correct reading is the original, the reply, and 12 later messages (14 total).
- Stopwords: STATS §2.3 listed "nahi" as a Hinglish stopword while §2.7 used it as a signature word. "nahi", "acha" and "chalo" are not stopwords.

**Why.** Tuning the generator until it hits a number that was only a guess would be backwards. The poster examples and tests now quote the measured values.

## D25. Filler text is template-composed

**Decision.** Only the scenes and the planted messages are hand-written. The filler between them is composed from phrase pools: a question gets an answer-shaped reply and conversations open like conversations, but neighbouring messages are otherwise unrelated.

**Why.** Every number in the project (stats, word clouds, search tests) works with it, and 47k hand-written messages are not realistic. I first measured how much padding the word-count adjuster was adding: 53,000 words, 19% of the chat, of "tbh" and "seriously". I fixed that by rebalancing message lengths until the natural total hit the target within 9 words, so no padding remains.

**Revisit if.** A recruiter reads the Exhibit A context closely and the filler shows. An offline LLM-written pass, committed like the rest of the output, would stay deterministic.

## D26. Stats are registry functions over one context

**Decision.** `lovelm.context.build_ctx` computes conversations, turns, replies, days, streaks and silences once, from the definitions in STATS §1.0. Each stat is a ~15-line function decorated with `@stat(id, priority, kind, theme, valence, ...)` that returns `Out(score, values, subject, quote_ids, n)`. The decorator applies the confidence factor, the Spicy gate and the catalog fields. Joke templates live in `copy.py` keyed by stat id, and a test fails if a stat has no copy or a bank entry has no stat. `analyze(chat, ...)` is cheap to call again, so reroll, the Spicy switch and nicknames are all just another call.

**Why.** Adding or changing a stat touches one function and one bank entry, and every stat is testable alone. Keeping computation (`stats/`), wording (`copy.py`) and choosing (`poster.py`) in three places means a joke can be rewritten without touching a number. **Rejected:** one class per stat (more ceremony for 15-line functions), and templates inside the stat functions (mixes numbers and wording).

## D27. Editorial ranking

**Decision.** A stat's rank is `round(score, 2) × charm`. `charm` is a visible, hand-set weight (0.45 for `msgs_per_day` up to 1.0 for `reply_median`, `longest_monologue`, `first_ily`, `apologies`). Scores equal to two decimals tie; ties go by charm, then by stat id. The laurel is filled first, so an equally extreme award stat is not spent as a critic quote. Countable stats are kept out of the critic slots and feed the rating box. Share-type stats (`peak_hour`, `night_owl_share`) score on the linear excess over a uniform baseline, because on a log scale a perfectly flat chat already scored 0.7.

**Why.** On the demo about a dozen stats score exactly 1.0, so a pure score ranking had no principled order. The first run produced "THE LONG REPLY" as the title instead of "2 AM AND STILL TYPING" because `reply_median` scored 1.0 and `peak_hour` scored 0.99999999995 (a confidence factor). That is floating-point noise deciding a poster, so near-ties are now real ties. Making the editorial weight explicit is more honest than pretending the data chose.

## D28. Archetypes: strong fits by priority

**Decision.** An archetype that fits a person strongly (score ≥ 0.85) is ranked by editorial priority (the funniest first), then by score. Weaker fits are ranked by score. Priorities: Ghost 1; Double Texter, Apologist, Notification Enthusiast 2; Philosopher, Romantic, Comedian 3; and so on.

**Why.** The sensitivity test (STATS §6.6) re-ran the demo with a 2 h and a 6 h conversation gap. At 2 h, Tara stopped being The Ghost and became The Voice-Note Enthusiast, on a score gap of 0.04; even at 4 h the Ghost led by 0.016 (0.964 against 0.948). Two archetypes that both fit someone that well are separated by noise, so the funnier one wins and the verdict no longer depends on a constant we chose. **Cost:** a funny archetype can beat a slightly better-fitting boring one; that is the intent.

## D29. Seeded variety

**Decision.** The book in `words_total_books`, the milestone, the line variant, the critic source, the star count among 2–3, the tagline and the fine print are chosen with a seeded RNG that uses only `random()` (stable across Python versions). The same seed gives byte-identical JSON; a reroll is a new seed; stat values never change with the seed.

**Why.** A reroll button has to actually change something, and a shared poster has to be reproducible. Tests assert both (six seeds give at least three different posters; seed 1234 twice gives identical JSON).

## D30. Third-party names

**Decision.** The quote guard rejects URLs, phone numbers, long digit runs, profanity, more than six words, and words only ever seen capitalised (probably names). It cannot catch a name in a chat typed entirely in lowercase: "cindy" passes. We accept that and rely on three escape hatches: one switch turns all quotes off, every poster line can be hidden, and the word cloud lets users tap a word to redact it.

**Why.** Reliable name detection needs a model or a name list, which costs size and still misses nicknames. All of this runs on the user's own device on their own chat, so the risk is what they *share*, and those three controls sit exactly at the point of sharing. **Revisit if** real samples show names leaking into poster lines.

## D31. Analysis speed

**Decision.** Measure, then optimize only what the profile points at. Pet-name detection (0.7 s) was indexed in M3. Nothing else is optimized.

**Measured for the 47,382-message demo (M4):**

| Where | Start Python | Read the chat | Analyze | Analyze, Spicy |
|---|---|---|---|---|
| Native CPython 3.13 | n/a | 0.3 s | 1.1 s | 1.3 s |
| Node 24 + Pyodide 0.29.5 | 0.6 s | 0.7 s | 2.3 s | 2.9 s |
| Chrome-based browser, steady state | 0.7 to 0.9 s | 0.6 to 0.9 s | 2.0 to 2.1 s | 2.6 s |

So WebAssembly is about 2× slower than native, and the browser matches Node. Rerolling and toggles each cost one analysis (about 2 s). **Extrapolation:** 100k messages is about 4.5 to 5 s, right at the PRD's 5 s budget; the 300k cap would take about 15 s, so the UI needs a visible progress state for big chats (the "typing…" screen already covers it).

**Caveat.** Some runs inside a throttled preview pane took 2 to 4× longer (4.2 s, 6 s, 10.7 s). The cause was never the engine: Python's own timer, a 1 ms render and a 26 KB result all checked out, and my first wall-clock timer included queueing. The UI now shows Python's own measurement. Background tabs may be slower on real phones, which are unmeasured (no real-device test yet).

**If it needs to be faster:** compute the per-message emoji and token tallies once (they are computed two or three times), run the per-lexicon passes in one sweep, and avoid recomputing stats when only the seed changes (the stats are seed-independent; only the line choices change).

## D32. Web shell

**Decision.** Vite + vanilla JS (22 KB, 8.9 KB gzipped, no framework). One page with five screens (landing, upload, who's who, processing, results) and a few small modules: `engine.js` (promise wrapper), `py.worker.js` (a classic worker with no imports, so it can `importScripts` Pyodide), `glue.py` (the only Python besides `lovelm`; every call returns coded JSON), `render.js`, `privacy.js`, `errors.js`, `dom.js`. The main thread passes the glue source to the worker. The page writes no `innerHTML` and no inline `style` attributes (it sets styles through the CSSOM), so a production CSP of `default-src 'none'; script-src 'self' 'wasm-unsafe-eval'; connect-src 'self'; worker-src 'self'; style-src 'self'; ...` holds. Chat text only ever enters the page as text.

**Why.** The strict CSP is part of the privacy claim: even a bug could not load a remote script or send data to another origin. I confirmed in a real browser that `wasm-unsafe-eval` is enough for Pyodide (no `unsafe-eval` needed), with no console violations. Vite's dev server does not apply the CSP (it injects inline styles for hot reload), so the CSP is added only in production builds and must be tested on `vite preview`.

## D33. The privacy readout is true by construction

**Decision.** The page records how many network requests it and the Python worker have made at the moment the chat is in memory, and later reports any new ones ("Network requests since your chat was in memory: 0"). The engine is always fully started *before* the file is read.

**Why.** The first version took the snapshot and then waited for Python to finish starting, so the engine's own startup downloads (`assets.json`, the wheel) appeared as "requests after your chat". They were static app files, but a privacy claim that is true only if the user is slow is not a claim. I found this by clicking the demo before Python was ready; the panel reported 2 requests. Now the claim holds regardless of timing, and I verified it in the production build with the CSP on: 0 requests, 11 files loaded before the chat, 0 external.

## D34. Pyodide 0.29.5, self-hosted

**Decision.** Pin `pyodide@0.29.5` (Python 3.13.2) and `vite@8.3.8` exactly, and copy the runtime into `web/public/pyodide/` at build time (`scripts/prepare-assets.mjs`). Nothing loads from a CDN.

**Why.** The registry's `latest` was a new `314.x` line published eight days earlier under a versioning scheme I had not seen, and I did not verify its Python version. 0.29.5 is the stable line and ships the same Python minor version (3.13) that every test ran on. The production build is 16 MB (Pyodide 11 MB, the demo chat 3 MB), and the wasm file compresses well over the wire. **Revisit:** move to the 314 line once it has some history and the core's tests pass on its Python.

## D35. Pyodide must equal native CPython

**Decision.** `web/scripts/smoke.mjs` runs the exact browser path (Pyodide, the wheel, `glue.py`) in Node and asserts the analysis is deeply equal to a native CPython run of the same demo. A Python test (`test_output_does_not_depend_on_hash_randomization`) asserts the same JSON under three different `PYTHONHASHSEED` values.

**Why.** The comparison found a bug none of my tests had: word-cloud ties were ordered by Python `set` iteration, which changes with the per-process hash seed, so CPython and Pyodide (and two CPython runs) disagreed on "service" versus "due". It also broke D29's promise that one seed gives identical output. Ties are now broken by the word itself. I confirmed the new test fails without the fix. **Note:** compare parsed values, not JSON text (`1.0` and `1` are the same number).

## D36. The poster is drawn on a canvas

**Decision.** The 1080 × 1920 poster is drawn directly on a `<canvas>` with the 2D API. The visible preview and the exported PNG are the same canvas, exported with `canvas.toBlob`. There is no HTML poster and no `html-to-image`.

**Why (supersedes D10).** I did not test `html-to-image` and found it wanting; I chose against it because three failure modes were known in advance and all apply here: (1) it embeds images by `fetch`ing them, which our CSP (`connect-src 'self'`) blocks for `blob:` URLs; (2) it serialises the DOM into an SVG `foreignObject`, which has long-standing font and image quirks in Safari, exactly where D10 flagged risk; (3) it is another dependency on the export path. A canvas gives one render path (what you see is exactly what you save), no serialisation, no dependency, and about 130 ms to export.

**Costs, and what covers them.** Canvas text is not selectable or announced, so the canvas has an `aria-label` describing the poster and the "Lines" panel lists every line as real text. The PNG is large (3.1 MB for the demo) because of the film grain. The layout, which would normally be CSS, is code (D39).

## D37. Fonts

**Decision.** Bebas Neue (titles, billing), DM Serif Display (regular and italic; quotes, tagline) and Inter 400 and 600 (small text), all SIL OFL 1.1. They come from `@fontsource/*@5.3.0`, installed as dev dependencies **after you approved the download**, using only the Latin subsets, and are bundled by Vite into the build (about 116 KB of woff2 that browsers fetch). Nothing loads from a CDN. The fonts are loaded at page start and awaited before the chat is read.

**Why.** Canvas only uses fonts that are already loaded, so the poster must wait for them. Loading them late also broke the privacy readout: the italic face is used only by the poster canvas, so it was requested after the chat was in memory and the readout correctly reported 1 request (the second time the readout caught a lazy load, after D33). **Honest note:** the build also emits the older `.woff` fallbacks (about 120 KB more in `dist/`) that modern browsers never request. **Limit:** names in non-Latin scripts fall back to the system font.

## D38. The photo never leaves the tab and never becomes a URL

**Decision.** A chosen photo is decoded with `createImageBitmap` (EXIF rotation applied), shrunk if over 2,400 px, cropped on a canvas, and given the poster look (a warm duotone ramp, a slight contrast curve and seeded grain) by a pixel loop. The result stays a canvas and is drawn straight into the poster. No `blob:` or `data:` URL is made for it. The user positions it with drag, a zoom slider, the mouse wheel or the arrow keys.

**Why.** The CSP never sees the photo, nothing can leak it through a URL, and a canvas is the cheapest thing to draw. The look is baked into the pixels (not a CSS filter or blend mode), so it is identical everywhere. Grain is seeded, so the same photo always gets the same grain.

## D39. A pure layout engine

**Decision.** `poster/layout.js` is a pure function from poster content and a `measure(text, font, tracking)` callback to a list of draw commands. It stacks the blocks from the bottom up (so the photo gets whatever room is left), fits the title to the width, and scales everything down if the content would swallow the photo. `draw.js` only executes the commands. 23 unit tests run it in Node with a fake measurer.

**Why.** It makes the layout testable without a canvas, and the tests found a real crash: when the layout scaled down and a billing line was too long, the font-size loop could step past its minimum and return `undefined`. Hiding a line draws a black `[REDACTED]` bar of the same height, so hiding never shifts the layout (also tested).

## D40. iPhone Safari is untested

**Status.** This Mac has only the Command Line Tools, not a full Xcode, so the iOS Simulator cannot run. The Chromium-based preview here is not WebKit. **Everything below is therefore unverified on WebKit**, and I did not work around it by capturing your screen or opening Safari on your desktop.

**What I relied on instead.** Standard canvas APIs (`toBlob`, `ellipse`, `createPattern`, `shadowBlur`), `document.fonts.load`, a fallback that spaces letters by hand when `ctx.letterSpacing` is missing, a fallback for `createImageBitmap` without options, and the Share and "Open image" paths for iOS's download quirks. Syntax needs Safari 15.4 or newer (`Array.prototype.at`).

**Checklist for the simulator (about 10 minutes).** On an iPhone simulator: (1) the app starts and the pill reads "Python 3.13.2 ready"; (2) the demo produces the poster and all five fonts render (not Georgia or Times); (3) Add a photo works, including HEIC from the photo library; (4) the letter-spacing on the small caps looks right; (5) "Share…" opens the share sheet with a PNG and "Open image" shows an image you can long-press to save; (6) analysis time on a real phone, not only the simulator.

## D41. Dueling Clouds: our own layout, real buttons

**Decision.** `web/src/cloud/layout.js` places the heaviest word first on the first free spot of an outward spiral from the centre. Words are horizontal boxes only and sizes follow the square root of the weight (STATS §2.4). If they do not all fit, the **whole cloud** scales down together (to 0.6x), and words that still do not fit at a readable size (11 px) are dropped. Each word is a real `<button>` positioned with CSS variables set through the CSSOM (the CSP forbids inline styles), so words are focusable, announced by screen readers, and tap-to-redact.

**Why.** It settles the open "d3-cloud vs wordcloud2.js" question by not needing either. Those libraries draw to a canvas or SVG with rotated words; ours are DOM elements, so redaction, accessibility and the CSP come for free, and the layout is a pure function tested in Node with a fake text measurer (like D39). Measured (Node, stand-in measurer): 33 ms for 30 words in 480x320, 159 ms for 60 words in 760x320, inside the 1 s budget of PRD §14.

**A bug worth recording.** The first version shrank only the word that did not fit, until it fitted. A long heavy word then came out *smaller* than lighter short ones, which makes a cloud lie about who says what more. The fix is the whole-cloud scale above; `test/cloud-layout.test.mjs` now has a test with a too-wide heavy word, and I checked that it fails when the old behaviour is put back.

**Costs.** No rotated words, so it looks less "cloud-like". In the Shared view only about 36 of the 60 candidate words fit, so it looks emptier than a library might. Spiral search is quadratic in the words placed: fine at 60, it would need a grid at hundreds.

**Revisit if** the v2 share-card (PRD §8.1) wants a rotated, prettier cloud as an image: a canvas library is reasonable there.

## D42. Browser tests: the production build, in the installed Chrome

**Decision.** `npm run e2e` builds, serves the **production** build (the one with the strict CSP; the dev server has none) and runs 9 Playwright tests in the system Google Chrome (`channel: "chrome"`). A `net` fixture records every request made by the page, its workers and anything else in the browser context, and at the end of each test fails on: a request that leaves the origin, any non-`GET`, any request with a body, or any console error (which includes CSP violations).

**Why.** It turns the privacy claim into something that fails loudly instead of something I promise. Using the system Chrome avoids a browser download that I would have had to ask you about (as with the fonts, D37).

**A finding worth keeping.** A test asserted that "Remove photo" brings the poster back pixel for pixel. It failed with 1,162,152 differing pixels (largest channel change 147). I first suspected an app bug (state leaking between draws) and reproduced it step by step. It was not the app: the trigger was the test's *own* second `getImageData` call. After two read-backs Chrome moves a canvas from GPU to software rasterisation, and the next draw differs slightly almost everywhere. Measured: 98% of the changed pixels moved by 1 to 3 levels, the mean change was 0.06, and 0.4% of pixels moved by more than 8 (mostly text edges). So the tests compare what is **visible** (mean change under 1; under 1% of pixels changed by more than 8 levels) and check that the same measure does notice a real change (a photo on the poster: mean change 9.4).

**Rejected.** `willReadFrequently: true` on the poster canvas (forces software rendering for every user just so a test can be exact). Dropping the assertion.

**Gap.** Chrome only. WebKit and Firefox are untested (D40).

## D43. Ready to deploy, not deployed

**Decision.** Everything needed to host the site is in the repository. The deployment itself has **not** happened: there is no git repository or remote here, and creating one and pushing is outward-facing and was not asked for. What exists:

- `.github/workflows/ci.yml`: Python tests on 3.11 and 3.13 plus the demo-freshness check; the web job (JS tests, Pyodide smoke test, Playwright in the runner's preinstalled Chrome); on `main`, a Pages deploy that needs both. The 404 page's "back" link is rewritten to `/<repo>/` for project sites (the rewrite was tested on a copy of the built page).
- The CSP as a `<meta>` tag (works on any static host) and a generated `web/dist/_headers` that adds `frame-ancestors 'none'`, `Referrer-Policy: no-referrer`, `Permissions-Policy`, and COOP/CORP. Cloudflare Pages and Netlify read it; **GitHub Pages ignores it**, so there the extra headers (and so `frame-ancestors`) do not apply.
- `404.html` ("Left on read."): self-contained, with its one `<style>` allowed by hash in its own CSP, and a test that fails if someone edits the CSS and forgets the hash.
- `licenses.txt`, generated at build from the font packages' own OFL texts, plus notices for Pyodide (MPL-2.0) and CPython (PSF-2.0) saying where the source and licence text are. Linked from the footer. I did not bundle the full MPL text; if the site is ever redistributed commercially, add it.
- A real `favicon.ico`, because the plain-text licences page and the 404 page made Chrome ask for one and log a console 404 (found by the privacy fixture, D42). A `<noscript>` note. A console message for the person who opens DevTools to check the privacy claim.

**Honest notes.** The workflow has never run, so expect a fix or two. Only Python 3.13 is installed here, so the 3.11 leg is unverified. I assume the runner's Chrome works with `channel: "chrome"`. Actions are pinned by major version tag, not commit SHA (easier to maintain, weaker against a compromised tag).

**Revisit if** the first CI run fails (fix it, do not loosen the tests), or hosting moves to a platform that reads `_headers`.

## D44. The anonymizer: scramble the content, keep the structure, prove it

**Decision.** `tools/anonymize_export.py` turns an export (`.txt` or iPhone `.zip`) into a **format sample**. It keeps timestamps exactly as written, speaker order, message lengths, punctuation, whitespace, emoji, invisible marks (iOS's U+200E, the narrow no-break space), WhatsApp's placeholders and the "edited" marker, and generic system notices. It replaces names (Person A, Person B, ...) and every letter, digit and mark of every message with a random one of the same kind. In system lines it replaces names, group subjects and phone numbers but keeps the words that make the parser see a system line (for example "changed the subject"). It keeps the first 300 messages by default, plus one later message if that is what it takes for the slice to show its own date order. It never changes the original and will not overwrite a file without `--force`.

**Why scramble, and not hash or substitute?** Hashing words keeps their identity: frequency analysis recovers content. Swapping in dictionary words can produce sentences that read like real ones. Random letters of the same kind keep length and shape and nothing else.

**Why keep timestamps?** Date-order inference (D14) depends on the real numbers. Shifting dates would change which days are above 12, which is the exact ambiguity a bug report about date order is about. The cost is that the sample still shows *when* people talked, and the tool says so.

**Verification, and the flaw the tests found.** Before writing, it parses the original and the sample and compares what the parser makes of them (each message's time, speaker order, kind and length; system lines; format; warnings). The first version compared only "same result, or same kind of error". A test with a deliberately broken scrambler showed that when the original is ambiguous, or otherwise fails to parse, both raise the same error, so the check passed without looking at the text: it was blind on exactly the files people report bugs about. Fixed: when the date order is not settled, every order is compared, structure and all. The tool is also mutation-tested: eight deliberate breakages (letters not replaced, placeholders scrambled, edited marker, one name for everybody, invisible marks dropped, system keywords, the date-order helper, a weak check) are each caught by a test.

**Limits.** Timestamps and message lengths leak activity patterns, and emoji are kept. It reuses a few parser internals (module-private by convention), so the tests fail if they drift. It has only been run on the demo chat and on generated exports, because no real export has been available (see the deferred table).

**Revisit if** a real export shows a quirk it mangles.

## D45. Redesign for simplicity, chosen by a design arena

**Why it was needed.** The owner tried it on a real chat and said, in short: not impressed by the design or the poster; why does it say "Python 3.13.2 ready"; it is dense and overly complicated; the copy is cliché ("Nobody interrupted. Nobody could."); how do you decide someone is "the philosopher"; how are affection and compliments counted. All fair. It was a stats dashboard wearing a costume: meters with weights, archetypes with runner-up scores (0.065), a reply-speed row reading "0.0167 vs 1", a seven-block blockbuster poster.

**Decision.** One path with one primary action per screen: landing → add your chat → names → five highlights → poster. Everything else is one level deeper in a sheet: "How we counted" (every number, a sentence each, and what counting cannot know) and "How it works" (the privacy count, the engine, every file loaded). Removed from the screens entirely: archetypes, the love and clingy meters, weights, scores, decimals, charts, Dueling Clouds, critic quotes, laurels, the rating box, the Spicy and quotes switches, reroll, the "Python ready" pill. The core still computes most of them (D46).

**How it was chosen (the arena).** One brief ([design/arena-brief.md](design/arena-brief.md): the owner's words, Apple's design guidance, the demo data, the CSP rules) went to three designers in parallel, each building a working prototype in its own folder: candidate 1 ("hmm", Opus), candidate 2 ("hi, is this Tara?", Opus; its first run on another model failed for lack of usage credits and was re-run), candidate 3 ("cinema", Sonnet). An independent judge (Sonnet, read-only) scored them on a rubric the designers never saw ([design/arena-rubric.md](design/arena-rubric.md)): path simplicity, copy, poster, interaction craft, phone quality, portability. Totals 25.5 / 26 / 24.5. Their screens: [candidate 1](design/candidate-1.jpg), [candidate 2](design/candidate-2.jpg), [candidate 3](design/candidate-3.jpg). The judge and I both picked **candidate 1 as the base**: the strongest poster by far (legible as a thumbnail, one idea), a declarative selection rule (five slots, each with a gate and a backup) and the smallest clean surface, even though candidate 2 scored half a point higher.

**Grafted in.** From candidate 2: the funniest true specifics ("Tara has sent 'hmm' 1,499 times in all", the reply counts behind each median), the six-dot silence timeline, and working browser Back (one history entry per screen). From candidate 3: the honest "We can't tell you why" for the silence. Fixes for what the judge found in the base: "answered within a minute" was said for up to two minutes; going Back while a chat was loading could later jump ahead (now every load has a token and a stale one is ignored); the poster's 31 bars had random widths (see D46).

**Rejected, and why.** Candidate 2's 24-hour clock as the poster image (true and pretty, but a second idea; every night-texting couple gets the same picture). Its film-credit lines ("music by 178 voice notes") as borderline cliché, the thing we were removing. Candidate 3's monthly pulse line on the poster (a second idea again) and its washed-out two-tone photo grade. More than five highlights, auto-advance, a light theme.

**Found while building it.** The base's spring capped each frame at 1/30 s, so when frames dropped (a busy or throttled page) every motion ran in slow motion; in a hidden pane at 2 frames a second the sheet never arrived. It now follows real time with small fixed sub-steps. The base's poster also could not fit a long run: the owner's own chat had 108 messages in a row, which made the bar spacing negative. Bar height now scales with the run (up to the 400 the core sends), with a test.

**Revisit if** someone on a real phone finds the highlights too few or too many, or the poster idea does not hold for a couple whose longest run is short (then the poster falls back to the two names as the title, which is plainer).

## D46. The words live in the front end; the poster's bars are real

**Decision.** `web/src/facts.js` writes every sentence a person reads, from the numbers the core sends. The core's own copy, poster selection, meters and archetypes still run (and are tested) but nothing on screen uses them; removing them is a separate cleanup. The longest-run stat now also sends `lens`: each message's length in characters (0 for a photo), at most 400. The poster draws one bar per message at that length (square-root scaled), so the picture is the run itself, not decoration.

**Why.** The copy needed to change faster than a wheel rebuild, and it needed the names typed on the names screen. Keeping it in one pure module means it is unit-tested against the demo couple: the five facts and their order, every backup, the twist only when true, no decimal, score or old verdict label anywhere, typed names everywhere except inside real quotes.

**Cost.** Two copy systems exist until the core's is removed. Message lengths are a little more of the chat in the result object; it never leaves the page either.

---

## Deferred on purpose (and when we decide)

| Question | Decide in | How |
|---|---|---|
| Real WhatsApp exports (formats, call lines, placeholder wording) | whenever a sample exists | Run it through `tools/anonymize_export.py` (D44), read the output, and add it as a fixture; the parser has only seen files I wrote |
| PNG export, fonts and the whole flow on iPhone Safari | as soon as full Xcode is installed | Install Xcode, run `sudo xcode-select -s /Applications/Xcode.app/Contents/Developer`, then run the checklist in D40 in the iOS Simulator |
| Real-device speed (phones) | when a phone is at hand | Time `analyze` on an actual phone (not done in M6) |
| ~~Word-cloud library (`d3-cloud` vs `wordcloud2.js`)~~ | M6 | Resolved by not using one (D41), then removed (D45) |
| Remove the core's unused copy, poster selection, meters and archetypes | next cleanup | Only after the new screens have met a real chat (D46) |
| Book word counts for the "Harry Potter" stat | M3 | Check each against a source; note the edition |
| Embedding model and Hinglish performance | M8 | Measure recall@5 on the demo's planted Hinglish set |
