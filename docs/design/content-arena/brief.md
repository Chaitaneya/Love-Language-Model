# Arena brief: what should Love Language Model show?

You are one of three designers working on the same brief in parallel. Build your best version; don't guess the others.

## Where we are

"Love Language Model" turns a WhatsApp chat export into a funny, shareable movie poster of a relationship, made from real numbers in the chat. The counting runs in the browser (Python on WebAssembly), so the chat never leaves the device. Audience: (1) a couple, on a phone, wanting a laugh and something to show people; (2) a recruiter with 30 seconds, who should smile.

It was just redesigned for simplicity (it used to be a cluttered stats dashboard: weighted "love meters", archetypes like "THE GHOST" with scores like 0.065, word clouds, charts, a seven-block poster). The redesign is one path: landing → add your chat → names → **five highlights** (one per screen) → **one poster** → a "How we counted" sheet one level deeper. A working copy is in `/tmp/arena-content/baseline/` (open `index.html` through a local server; any chosen file or "Try it with a demo couple" loads the demo couple).

## What the owner said now (read it twice)

> "Now it is good, but there are too little things to show anyone. I don't know what to keep and what not to keep: decide."

So the redesign over-corrected: it is clean, but after five screens and one poster there is not much worth showing a partner, a friend or a group chat. The owner's earlier complaints still stand and must not come back: no jargon on the main path ("Python 3.13.2 ready"), no scores, weights or decimals, nothing dense or overly complicated, no cliché punchlines ("Nobody interrupted. Nobody could."), and nothing we cannot explain honestly in one sentence ("how are we judging Chaitanya is the philosopher?").

Your job: **decide what the product shows, and build it.** More to show, without losing the simplicity. That tension is the whole brief.

## What exists (all of it real, for the demo couple Rohan and Tara)

`/tmp/arena-content/baseline/demo/demo-result.json` (and `demo-result-spicy.json`, which adds spicy stats) is the full analysis. Inspect it. In short:

- `stats`: 37 stats (45 with Spicy), each `{id, subject, values{...}, lines}`. The `lines` are the OLD cliché copy; do not reuse their tone. Used today: first_message, reply_median, longest_monologue, busiest_day (+ longest_silence, longest_streak), first_ily; the rest only appear as one-line receipts in the sheet. Unused or barely used: signature_words, emoji_top, double_texts, deleted, runtime_typing, reel_dealer (links sent), voice_notes, message_milestones (message 5,000 with its quote), left_hanging, night_owl_share, peak_hour, initiator, last_word, affection_count, makes_laugh, questions, goodnight_ritual, emoji_per_person, swearing, one_word_replies, words_per_message, early_bird, message_share, reply_fast_share, ok_period, pet_name, words_total_books, span_days, msgs_per_day; spicy: apologies, fight_days, clingy_pings, silence_breaker, triple_texts, bang_then_silence, night_starter, who_is_that.
- `charts`: `heartbeat` (messages per month per person), `heatmap` (weekday x hour), `reply_hist` (reply-time buckets per person), `hours` (messages per hour per person).
- `words`: `dueling` (each person's most distinctive words, with counts `nA`/`nB` and a log-odds z), `shared` (words both use), `hidden` (probable names of third parties, never shown unless asked).
- `meters` and `archetypes`: the old weighted love meter and archetype labels. The owner rejected both as they were presented; if you bring any of it back, it must be honest and explainable in one sentence, and you must say why.
- `meta`: range, message count, conversations.

How each number is computed is in `core/lovelm/` (read only; `stats/*.py`, `context.py`, `lexicons/`) and `docs/STATS.md`. Any "how we know" sentence you write must be true to that code.

## Design rules (from the owner and Apple's design guidance)

Read Apple's guidance end to end before designing:
Apple's design guidance (fluid interfaces, the eight design principles, typography)

Especially: Purpose (decide what not to build), Simplicity not minimalism (the common path first, the rest one level deeper; sometimes *adding* context simplifies), Familiarity and consistency (things that look the same behave the same), Craft, and Delight as the result of the rest.

- Every fact shown is specific (a number, date, time or quote from the data), true to the code, and comes with one plain "how we know" sentence.
- Dry, warm, specific copy; the number is the joke; never mean; never a verdict about a person's feelings.
- Privacy: quotes are short and already filtered by the core; never show `words.hidden`; anything that could embarrass should be easy to leave out of what gets shared.
- Keep the existing look (dark room, DM Serif Display for big type, system font for UI, one red accent, the cream "hmm" poster) unless you have a strong reason, and say it.

## What to build

1. **A decision, item by item.** In `DECISION.md`: a table of every stat id, chart, word list, meter and archetype in the JSON, each marked **keep where it is / move / add / cut**, with where it lives (main path, a new place, the receipts, nowhere) and a one-line reason. Then the structure you chose (what the person sees, in order) and why.
2. **A working prototype of that decision.** Copy `/tmp/arena-content/baseline/` into your folder and change it. Same tech: plain HTML/CSS/vanilla ES modules, no build step, no npm, no network beyond your own folder, CSP-safe (no inline scripts or `style=` attributes, no `innerHTML` with data; dynamic styles via `el.style.setProperty`). Keep `engine.js`, `privacy.js` and `errors.js` as they are (they are stand-ins for the real app's modules with the same API). All copy stays in `facts.js` (or modules like it): pure functions over the result JSON, no DOM, so it can be unit-tested.
3. **`RATIONALE.md`**: your direction in a few paragraphs, every new copy line with its data source, the alternatives you considered and rejected and why, and known weaknesses.
4. **`shots/`**: screenshots at 390x844 of every screen and state you added or changed, one at 1280x800, and any exported image(s) you produce.

## How to run and check

`python3 -m http.server <PORT> --directory <your folder>` in the background (kill it when done). Playwright from the existing install, with the installed Chrome:

```js
import { createRequire } from "node:module";
const require = createRequire("<repo>/web/package.json");
const { chromium } = require("@playwright/test");
const browser = await chromium.launch({ channel: "chrome", headless: true });
```

Look at your own screenshots and iterate until you would defend them in front of Apple's design team. No console errors; no sideways scroll at 390 px.

## Forbidden

Writing outside your own folder (never write in the project repository), `npm install`, network fetches, git, and using any chat other than the demo JSON.
