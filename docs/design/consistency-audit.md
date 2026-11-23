# Consistency audit (Apple design guidance), after the D45 redesign

Method: read `web/src/style.css`, `index.html`, `main.js`, `reveal.js`, `sheet.js`, `poster.js` and `facts.js` end to end; measured in Chrome at 390 x 844 where a claim depended on layout. Each item names the principle it breaks. "Confirmed" means measured; the rest are read from the code.

## Layout and spacing

1. **Two left edges on the highlights screen** (Craft: nothing random). The fact text starts at 28 px, the back button and the Next button at 20 px (the gutter). *Confirmed.* Fix: the slide uses the gutter.
2. **The highlights screen scrolls** (Craft: jittery scroll reads as careless). It is exactly the viewport tall, but the footer links sit below it: the page is 883 px in an 844 px window. *Confirmed.* Fix: the footer is part of the landing page only (it is where "How it works" belongs before a chat is read); later screens reach it from their own controls.
3. **Controls of the same kind have different heights and corners.** Buttons 52 px with 14 px corners, name fields 56 px with 12 px, the segmented control 48 px with 12 px (its segments 9 px), the drop zone 20 px, the sheet 18 px, the error dialog 20 px. Fix: two radii, 14 px for controls and 20 px for surfaces, with nested corners derived from them (outer minus padding); fields 52 px like buttons.

## Type

4. **Five different "eyebrow" label styles for one role.** Wordmark 12 px at +0.14 em; export steps title 12 px at +0.08 em; highlight kicker 13 px at +0.07 em; "How we know" 11 px at +0.10 em; receipt section titles 12 px at +0.08 em. Fix: one eyebrow style (12 px, 600, +0.08 em, the tertiary colour); the kicker stays larger because it is the fact's lead-in, and the wordmark keeps its wider tracking as a logotype.
5. **Off-scale text sizes.** Small text comes in 12, 13, 14 and 15 px; 14 px sits between the footnote (13) and subheadline (15) steps and is used for five unrelated things. Fix: snap to the scale 12 / 13 / 15 / 17 / 19.
6. **Same size, different tracking.** The 40 px landing title is tracked -0.018 em, the 40 px "Tara said 'I love you' first" -0.016 em; 15 px text is -0.005 em in one place and inherits -0.01 em in four others. Tracking should be a function of size only. Fix: size-specific tokens.
7. **The near-duplicate serif sizes** 26 px (loading line) and 28 px (sheet titles, dialog titles). Fix: one 28 px step.

## Colour

8. **Hard-coded colours outside the tokens**: two pressed-state colours, the poster paper twice, three different translucent creams, and two different scrims (the sheet's 0.6 black and the dialog's). Fix: tokens for each, one scrim.
9. **The same role in two greys.** Secondary notes use the secondary grey in some places and the tertiary grey in others (the hint vs the status line; the privacy note vs the loading note). Fix: secondary grey for anything you are meant to read, tertiary only for labels.

## Behaviour

10. **Two link styles do the same thing.** "How we counted all this ^" and the footer's "How it works" both open a sheet, but one has a chevron and no underline, the other is an underlined footer link (Familiarity: things that look the same behave the same, and the reverse). Fix: everything that opens a sheet looks the same.
11. **Same place, different meaning.** The top-right text button is "Skip" on the highlights and "Start over" on the poster. "Start over" throws away the chat, the poster and the photo, with no warning (Agency, forgiveness; a confirmation only for the truly destructive). Fix: "Start over" asks once, and reads as what it is.
12. **Three press feedbacks.** Buttons scale to 0.97 in 60 ms; icon, text and link buttons fade to 0.5 and scale 0.96 in 40 ms; segments 0.96 in 40 ms; the drop zone 0.98 in 60 ms (Response: one consistent feel). Fix: one press token.
13. **Reduced motion is partial**: the press scale is removed from buttons but not from icon, text and link buttons. Fix: the same rule everywhere.
14. **The error dialog appears with no motion** while everything else moves (Craft, spatial consistency). Fix: it fades and scales in like a material arriving, and only fades under reduced motion.
15. **Screens move by CSS keyframes (420 ms) while the reveal and the sheets use springs (about 0.38 s).** Acceptable (screens are button-driven), but the duration should match the springs. Fix: 380 ms.

## Words

16. **Two quote styles for one phrase**: the highlights say “I love you” (curly double quotes), the poster says ‘I love you’ (single). Fix: one style.
17. **Two date formats in one sheet**: "14 June 2024" in the highlights, "2 Feb 2024 to 2 Aug 2024" in the receipts. Fix: long dates in the app, short ones only on the poster where space is tight.
18. **The demo link reads two ways**: "Try it with a demo couple" on the landing, "No chat handy? Use the demo couple" on the add screen. Fix: one name for one action.
