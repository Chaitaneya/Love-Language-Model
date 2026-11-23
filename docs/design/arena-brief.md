# Arena brief: redesign "Love Language Model" for simplicity

You are one of three designers working on the same brief in parallel. Build your best version. Do not try to guess the others.

## The product, in one paragraph

A couple drops in a WhatsApp chat export and gets a funny, shareable **movie poster of their relationship**, made from real numbers in their chat (who texts first, who replies in 23 minutes, who said "ok." 38 times). The analysis runs entirely in the browser (Python on WebAssembly), so the chat never leaves the device. Audience: (1) a couple, on a phone, wanting a laugh and something to post; (2) a recruiter with 30 seconds, who should smile.

## What the owner said about the current version (read it twice)

- "I am not impressed by the design and the image poster too."
- "Why is there 'Python 3.13.2 ready' written on top?" (engineering jargon on the main screen)
- "You have made it way too complex for someone using it. It is so dense and things are overly complicated."
- "Things sound very cliché", e.g. *"Chaitanya once sent 108 messages in a row. Nobody interrupted. Nobody could."*
- "How are we judging Chaitanya is the philosopher?" (the UI showed archetype runner-ups with raw scores like 0.065)
- "How are we calculating affection, compliments?" (the UI showed a weighted table with "reply speed 0.0167 vs 1")

The diagnosis we agreed on: it is a stats dashboard wearing a costume. The fix is **purpose and simplicity**: one path, one idea per screen, plain language, the specific fact *is* the joke, details one level deeper.

## Design principles you must work from

Read this file end to end first (Apple's design guidance translated for the web):
Apple's design guidance (fluid interfaces, the eight design principles, typography)

The ones that matter most here: Purpose (decide what not to show), Simplicity not minimalism (hierarchy, plain words, common path first, advanced one level deeper), Familiarity, Craft (typography: size-specific tracking and leading; every value defensible), Response (feedback on pointer-down), Interruptibility and springs for anything you touch, Spatial consistency (things leave the way they came), Reduced motion.

## The data

`/tmp/arena-redesign/shared/demo-result.json` is the real output of the analysis for the **demo couple, Rohan and Tara** (synthetic; 47,382 messages over 659 days). `demo-result-spicy.json` is the same with "Spicy" mode on (adds apologies, clingy stats). Use these and nothing else. Never ask for or use any real chat.

Shape: `people.A.name / people.B.name`; `meta` (range, messages, conversations); `stats` = list of `{id, subject ("A"|"B"|null), score, values{...}, lines[...]}` (the `lines` are the OLD cliché copy: do not reuse their tone); `poster` (old poster content); `meters.love` (old weighted meter: do not surface weights or decimals); `archetypes`; `words.dueling` (each person's distinctive words); `charts` (heartbeat = messages per month, hours = messages per hour of day per person).

Useful `values` (all real numbers in the file): `longest_monologue {n, W, L, date, q}` (Rohan sent 31 in a row on 2024-06-14; Tara replied "hmm"), `reply_median {sec_a, sec_b, fast, slow}` (Rohan 100 s, Tara 1375 s), `ok_period {a, b}` (Tara sent 38 "ok."), `first_ily {n:47 days, W, date}`, `pet_name {token:"babu", n, a, b}`, `double_texts`, `emoji_top {emoji, n}`, `longest_silence {d, start, end}`, `busiest_day {date, n, median}`, `longest_streak {n, start, end}`, `peak_hour {hour_label, pct}`, `first_message {q, date, W}`, `initiator {pct, W}`, `message_milestones {n, date, q, W}`, `runtime_typing {hours}`, `words_total_books {x, book}`, and more. Inspect the file.

## What to build

A clickable, **phone-first** prototype of the new experience, in plain HTML + CSS + vanilla ES modules (no framework, no build step, no npm install, no network requests except to its own folder). It reads the JSON above (copy it into your folder). It must cover:

1. **Landing.** What this is in one sentence, one primary action, one line about privacy in plain words. No technical status text on this screen (a "how it works" link lower down or deeper is fine).
2. **Add your chat.** A simple drop/choose step. In the prototype, choosing any file (or a "try the demo couple" action) loads the demo JSON. Include a calm loading state (analysis takes 2-5 s in reality; simulate ~2 s).
3. **Names.** Confirm the two names (prefilled, editable). One screen, one button.
4. **The reveal.** A short sequence (you decide how many; fewer is better) of the most telling facts, one per screen, big type. Each fact is **specific** (a real number, date, time or quote from the data) and carries one plain-language line saying how we know. Choose the facts with a rule you can defend, and make sure facts never contradict each other (or, better, turn an apparent contradiction into the joke). Swipe, tap or arrow keys to move; spring-based, interruptible.
5. **The poster.** A redesigned 1080 x 1920 poster drawn on a `<canvas>` (canvas is required: it is also the exported PNG). Restraint, one idea, A24-poster level of taste rather than a blockbuster with seven text blocks. Must look good **without** a photo and **with** one (let the user pick an image file; process it on a canvas, never upload it). A "Save image" action that produces a real PNG (`canvas.toBlob`). Optional: hide a line, choose between a couple of title options. Keep the controls few.
6. **The receipts.** One level deeper (a bottom sheet you can drag down with velocity, or a separate view): every fact in plain language, with "how we counted it" in a sentence each. No weights, no decimals, no scores. Honest about what keyword counting can and cannot know.

Write the copy yourself, from `values`. Tone: dry, specific, warm, never mean. Rewrite cliché into specificity: the number, the date, the reply. Prefer understatement. No "Nobody could."-style punchlines.

## Constraints (the real app's rules, so your work can be ported)

- Strict CSP in production: no inline `<script>` or `style="..."` attributes, no `innerHTML` with data (build DOM with `createElement` / `textContent`; set dynamic styles through `el.style.setProperty`). External CSS file and module scripts only.
- No external network: fonts must be local. You may use the system font stack (`system-ui, -apple-system, ...`) and/or the font files in `/tmp/arena-redesign/shared/fonts/` (Bebas Neue, DM Serif Display regular/italic, Inter 400/600; copy what you use). Canvas text needs the font loaded first (`document.fonts.load`).
- `prefers-reduced-motion` respected. Keyboard reachable. Text contrast AA. Works at 390 px wide with no horizontal scroll, and still looks intentional at 1280 px.
- Keep it small and readable. Plain functions, no clever abstractions. A future maintainer ports this into an existing Vite app.

## Deliverables (in YOUR folder only)

- `index.html`, `style.css`, `app.js` (+ any other modules), a copy of the JSON.
- `RATIONALE.md`: your design direction in a few paragraphs; the reveal-selection rule; how the poster works; every copy line you wrote and the data it comes from; **the alternatives you considered and rejected, and why**; known weaknesses.
- `shots/`: screenshots you took of your own prototype: at 390x844 (landing, names, two reveal screens, poster without photo, poster with photo, receipts) and one at 1280x800. Also save the exported poster PNG as `shots/poster.png`.

## How to run and screenshot

Serve your folder: `python3 -m http.server <PORT> --directory <your folder>` (run it in the background, kill it when done). Use Playwright from the existing install, with the installed Google Chrome:

```js
import { createRequire } from "node:module";
const require = createRequire("<repo>/web/package.json");
const { chromium } = require("@playwright/test");
const browser = await chromium.launch({ channel: "chrome", headless: true });
```

Look at your screenshots (open the PNG files) and iterate until you would defend them in front of Apple's design team. Fix what looks off. Check the browser console has no errors.

## Forbidden

- Writing anywhere outside your own folder. Do not touch the project repository (read it if useful, never write).
- `npm install`, any network fetch, git commands.
- Using any chat other than the demo JSON.
