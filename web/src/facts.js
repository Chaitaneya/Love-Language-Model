// Turns the analysis result into words. Pure functions, no DOM: unit-tested in test/facts.test.mjs.
//
// Everything a person reads comes from here: the reveal facts, the poster lines and the receipts.
// Each writer takes a stat's values and returns plain copy, or null when the stat is missing or too
// weak to say something true and interesting. The number is the joke; the copy never explains it.
// No scores, weights or decimals ever reach the page (docs/decision.md D45).

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
  "September", "October", "November", "December"];
const WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
  "eleven", "twelve"];

export const int = (n) => Math.round(n).toLocaleString("en-US");
export const word = (n) => (n >= 0 && n <= 12 ? WORDS[n] : int(n));
const capital = (s) => s.charAt(0).toUpperCase() + s.slice(1);

function parts(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return { y, m, d };
}
export function longDate(iso) {
  const { y, m, d } = parts(iso);
  return `${d} ${MONTHS[m - 1]} ${y}`;
}
export function shortDate(iso) {
  const { y, m, d } = parts(iso);
  return `${d} ${MONTHS[m - 1].slice(0, 3)} ${y}`;
}
const dayMonth = (iso) => { const { m, d } = parts(iso); return `${d} ${MONTHS[m - 1]}`; };

/** 40 s, 1 min 40 s, 23 min, 2.5 hours. Never rounds a minute and a half up to "2 minutes". */
export function duration(sec) {
  if (sec < 60) return `${Math.round(sec)} s`;
  if (sec < 600) {
    const m = Math.floor(sec / 60);
    const s = Math.round(sec % 60);
    return s ? `${m} min ${s} s` : `${m} min`;
  }
  if (sec < 5400) return `${Math.round(sec / 60)} min`;
  return `${Math.round(sec / 360) / 10} hours`;
}
function times(ratio) {
  const r = Math.round(ratio);
  return r === 2 ? "twice" : `${word(r)} times`;
}
const daysBetween = (a, b) => Math.round((Date.parse(b) - Date.parse(a)) / 86400000);

// -------------------------------------------------------------------- context
export function makeContext(data, names) {
  const stats = {};
  for (const s of data.stats) stats[s.id] = s.values;
  const other = (side) => (side === "A" ? "B" : "A");
  // Every card puts each person on the same side: the one who sent the longest run on the right, where
  // your own messages sit in a chat, and the one who answered on the left.
  const run = stats.longest_monologue;
  const right = run && run.n >= 12 ? run.win : "A";
  return {
    data, stats, names, name: (side) => names[side], other, first: data.meta.range[0], last: data.meta.range[1],
    sides: [other(right), right],
  };
}

/** How many times one person used a word, from the distinctive-words table (null if it is not there). */
function wordCount(c, w, side) {
  const key = side === "A" ? "nA" : "nB";
  for (const list of [c.data.words?.dueling?.A, c.data.words?.dueling?.B, c.data.words?.shared]) {
    const hit = (list || []).find((x) => x.w === w.toLowerCase());
    if (hit) return hit[key];
  }
  return null;
}

// -------------------------------------------------------------- reveal facts
//
// Five questions, asked in story order. For each, the first stat that can answer it with something
// concrete (a quote, a date or a time) wins. A stat that cannot answer it plainly (too close to call,
// no quote, too small) returns null and its backup gets a turn.

export const SLOTS = [
  ["first_message", "message_milestones"], // How did it start?
  ["reply_median", "double_texts"], //          Who is quicker?
  ["longest_monologue", "ok_period"], //        Who talks, who answers?
  ["busiest_day", "longest_streak"], //         The biggest day.
  ["words"], //                                 How do you each sound? (from words.dueling, not a stat)
  ["first_ily", "pet_name"], //                 The turn.
];

const REVEAL = {
  first_message(v, c) {
    if (!v.q) return null;
    return {
      id: "first_message",
      label: `The first message, ${longDate(v.date)}`,
      kicker: longDate(v.date),
      big: `“${v.q}”`,
      bigStyle: "quote",
      line: `The first message, from ${c.name(v.win)}. ${int(c.data.meta.messages - 1)} more followed.`,
      how: "The first message in the chat that isn’t a WhatsApp notice.",
    };
  },
  message_milestones(v, c) {
    if (!v.q) return null;
    return {
      id: "message_milestones",
      label: "A milestone message",
      kicker: `Message ${int(v.n)} · ${longDate(v.date)}`,
      big: `“${v.q}”`,
      bigStyle: "quote",
      line: `Sent by ${c.name(v.win)}.`,
      how: `We counted every message from the first one and stopped at number ${int(v.n)}.`,
    };
  },
  reply_median(v, c) {
    if (v.r < 3) return null; // too close to be a story
    const slow = v.slow_side;
    const fast = c.other(slow);
    const hist = c.data.charts?.reply_hist;
    const sum = (k) => (hist?.[k] || []).reduce((a, b) => a + b, 0);
    const counts = hist ? ` From ${int(sum(fast))} of ${c.name(fast)}’s replies and ${int(sum(slow))} of ${c.name(slow)}’s.` : "";
    return {
      id: "reply_median",
      label: "Reply times",
      kicker: "How long a reply usually takes",
      rows: [
        { name: c.name(fast), value: duration(fast === "A" ? v.sec_a : v.sec_b) },
        { name: c.name(slow), value: duration(slow === "A" ? v.sec_a : v.sec_b), accent: true },
      ],
      line: `Same conversations, about ${times(v.r)} the wait.`,
      how: "For each of you, the middle of all the gaps between the other person’s message and your answer. "
        + `Four quiet hours start a new conversation, so sleep doesn’t count.${counts}`,
    };
  },
  double_texts(v, c) {
    if (v.r < 3) return null;
    return {
      id: "double_texts",
      label: "Double texts",
      kicker: "Double texts",
      rows: [
        { name: c.name(v.win), value: int(v.w), accent: true },
        { name: c.name(c.other(v.win)), value: int(v.l) },
      ],
      line: `${c.name(v.win)} rarely waits for an answer.`,
      how: "A second message sent ten minutes or more after your own last one, with no reply in between.",
    };
  },
  longest_monologue(v, c) {
    if (v.n < 12 || !v.q) return null;
    const replier = c.other(v.win);
    const often = wordCount(c, v.q, replier);
    return {
      id: "longest_monologue",
      label: `The longest run, ${longDate(v.date)}`,
      kicker: longDate(v.date),
      big: `${int(v.n)} messages in a row`,
      bigStyle: "number",
      visual: { kind: "monologue", lens: v.lens || [], n: v.n, reply: v.q },
      line: `All from ${c.name(v.win)}. Then ${c.name(replier)} replied.`
        + (often >= 20 ? ` ${c.name(replier)} has sent “${v.q}” ${int(often)} times in all.` : ""),
      how: "The longest run of messages from one person before the other wrote back. Each bar is one message, as long as it was.",
    };
  },
  ok_period(v, c) {
    if (v.n < 10) return null;
    return {
      id: "ok_period",
      label: "“ok.”",
      kicker: `From ${c.name(v.win)}, ${int(v.w)} times`,
      big: "“ok.”",
      bigStyle: "quote",
      line: "With the full stop.",
      how: "Messages that are exactly “ok.” or “okay.”, full stop included. We can’t tell how it was meant.",
    };
  },
  busiest_day(v, c) {
    if (v.x < 5) return null;
    const s = c.stats.longest_silence;
    const streak = c.stats.longest_streak;
    const after = s && s.start === v.date && s.d >= 2;
    const endedStreak = streak && streak.end === v.date && streak.n >= 30;
    return {
      id: "busiest_day",
      label: `The busiest day, ${longDate(v.date)}`,
      kicker: longDate(v.date),
      big: `${int(v.n)} messages`,
      bigStyle: "number",
      visual: after ? { kind: "gap", from: dayMonth(s.start), to: dayMonth(s.end), days: s.d } : null,
      line: after
        ? `Your busiest day, ${times(v.x)} a normal one. Then ${word(s.d)} days without a word, until ${c.name(s.win)} wrote first.`
        : `Your busiest day, ${times(v.x)} a normal one.`,
      how: [`A normal day for you two is ${int(v.median)} messages.`,
        endedStreak ? `It was also the last day of a ${int(streak.n)}-day streak.` : "",
        after ? `${capital(word(s.d))} days is the longest quiet in the whole chat. We can’t tell you why.` : ""].filter(Boolean).join(" "),
    };
  },
  longest_streak(v) {
    if (v.n < 30) return null;
    return {
      id: "longest_streak",
      label: "Longest streak",
      kicker: `${longDate(v.start)} to ${longDate(v.end)}`,
      big: `${int(v.n)} days in a row`,
      bigStyle: "number",
      line: "Both of you, every day.",
      how: "Days on which both of you sent at least one message, one after another. A day ends at 5 AM.",
    };
  },
  first_ily(v, c) {
    if (!v.n) return null;
    const reply = c.stats.reply_median;
    const other = c.name(c.other(v.win));
    const said = [];
    if (reply && reply.r >= 3 && reply.slow_side === v.win) said.push("Slower to reply, first to say it."); // the twist
    if (v.dur != null && v.dur <= 60) said.push(`${other} answered within a minute.`);
    return {
      id: "first_ily",
      label: `Who said it first, ${longDate(v.date)}`,
      kicker: `Day ${int(v.n)} · ${longDate(v.date)}`,
      big: `${c.name(v.win)} said “I love you” first.`,
      bigStyle: "statement",
      line: said.length ? said.join(" ") : `${int(v.n)} days after the first message.`,
      how: "The first message from either of you with “I love you”, “love you” or a close spelling. Days count from the first message.",
    };
  },
  words(_v, c) {
    const pools = wordPools(c);
    const shown = chooseWords(pools);
    if (shown.A.length < 2 || shown.B.length < 2) return null;
    const punch = punchWord(c, shown);
    return {
      id: "words",
      label: "Who says what",
      kicker: "Who says what",
      big: null,
      visual: {
        kind: "duel",
        cols: c.sides.map((side) => ({
          name: c.name(side),
          words: shown[side].map((x) => ({ w: x.w, note: `${int(x.mine)} · ${c.name(c.other(side))} ${int(x.theirs)}` })),
        })),
      },
      line: punchLine(c, punch),
      plain: `${c.name("A")}: ${shown.A.map((x) => x.w).join(", ")}. ${c.name("B")}: ${shown.B.map((x) => x.w).join(", ")}. ${punchLine(c, punch)}`,
      how: WORDS_HOW,
    };
  },
  pet_name(v, c) {
    return {
      id: "pet_name",
      label: "Pet name",
      kicker: "Your word for each other",
      big: `“${v.token}”`,
      bigStyle: "quote",
      line: `${int(v.n)} times. ${c.name("A")} ${int(v.a)}, ${c.name("B")} ${int(v.b)}.`,
      how: "The word that most often follows “love you”, “good morning” or “hi”, counted as a whole word.",
    };
  },
};

export function pickFacts(c) {
  const out = [];
  for (const candidates of SLOTS) {
    for (const id of candidates) {
      const v = id === "words" ? c.data.words : c.stats[id];
      const fact = v ? REVEAL[id](v, c) : null;
      if (fact) {
        out.push(fact);
        break;
      }
    }
  }
  return out;
}

// ------------------------------------------------------------------ the cards
//
// Three cards on one grid: the poster, who says what, and the cast. Everything drawn on a card can be left
// off it. `off` is a Set of item keys ("line:run", "word:A:bro", "role:initiator", "extra:pet"); each card
// returns `chips`, the items a person can tap to leave out, grouped by who they belong to.

function totalsCredits(c) {
  return [
    `${int(c.data.meta.messages)} messages · ${int(daysBetween(c.first, c.last))} days`.toUpperCase(),
    `${shortDate(c.first)} – ${shortDate(c.last)}`.toUpperCase(),
  ];
}
const chipsOf = (items, off) => items.map((i) => ({ key: i.key, text: i.chip ?? i.text, on: !off.has(i.key) }));

export function posterContent(c, off = new Set()) {
  const m = c.stats.longest_monologue;
  const ily = c.stats.first_ily;
  const run = m && m.n >= 12 ? m : null;
  const titles = [];
  if (run && run.q && run.q.length <= 8) titles.push({ key: "word", text: run.q });
  titles.push({ key: "names", text: `${c.name("A")} & ${c.name("B")}` });

  const items = [];
  if (run) items.push({ key: "line:run", chip: `${int(run.n)} in a row`, text: `${c.name(run.win)} sent ${int(run.n)} messages in a row.` });
  if (ily) items.push({ key: "line:ily", chip: "“I love you” first", text: `${c.name(ily.win)} said “I love you” first.` });

  return {
    kind: "poster",
    titles,
    monologue: run ? { n: run.n, lens: run.lens || [] } : null,
    left: c.name(c.sides[0]),
    right: c.name(c.sides[1]),
    lines: items.filter((i) => !off.has(i.key)).map((i) => i.text),
    chips: [{ label: "Lines", items: chipsOf(items, off) }],
    credits: totalsCredits(c),
    fileName: "love-language-model-poster", // deliberately no names in the file names
  };
}

// ---- who says what
// Words that would embarrass on a shared card stay off it unless chosen: swear words (the core never
// prints its list) and apologies (the core keeps apology counts behind Spicy). Matched like the core
// matches: lower case, runs of one letter collapsed ("sorryyy" is "sory").
const squash = (s) => s.toLowerCase().replace(/(\p{L})\1+/gu, "$1");
const KEEP_OFF = new Set(["sorry", "sry", "maaf", "maafi", "apologies", "apologise", "apologize",
  "damn", "wtf", "crap", "hell", "shit", "bullshit", "fuck", "fucking", "fck", "asshole", "bastard", "bitch",
  "dick", "piss", "pissed", "bloody", "madarchod", "behenchod", "bhenchod", "chutiya", "bhosdike", "gaandu",
  "harami"].map(squash));
const WORDLIKE = /^\p{L}[\p{L}\p{M}'’]*$/u; // a word, not an emoji or a number

export const WORDS_HOW = "We compared how often each of you uses every word. These are the most lopsided ones, "
  + "said at least twice as often by one of you. A word needs eight uses between you to count, and names of other people are left out.";

/** Each person's most distinctive words, best first, as the core ranked them. Never words.hidden. */
export function wordPools(c, max = 8) {
  const hidden = new Set((c.data.words?.hidden || []).map((x) => x.w));
  const pet = c.stats.pet_name?.token; // the pet name is both of yours: it gets its own billing on the cast card
  const pool = (side) => (c.data.words?.dueling?.[side] || [])
    .map((x) => ({ key: `word:${side}:${x.w}`, w: x.w, side, mine: side === "A" ? x.nA : x.nB, theirs: side === "A" ? x.nB : x.nA }))
    .filter((x) => WORDLIKE.test(x.w) && !hidden.has(x.w) && x.w !== pet && !KEEP_OFF.has(squash(x.w)) && x.mine >= 2 * x.theirs)
    .slice(0, max);
  return { A: pool("A"), B: pool("B") };
}

export function chooseWords(pools, off = new Set(), n = 3) {
  const pick = (list) => list.filter((x) => !off.has(x.key)).slice(0, n);
  return { A: pick(pools.A), B: pick(pools.B) };
}

/** The most lopsided top word, skipping the longest run's reply (the story has already used it). */
function punchWord(c, shown) {
  const reply = (c.stats.longest_monologue?.q || "").toLowerCase();
  const tops = [shown.A[0], shown.B[0]].filter(Boolean);
  const fresh = tops.filter((x) => x.w !== reply);
  const pool = fresh.length ? fresh : tops;
  return pool.sort((a, b) => (b.mine + 1) / (b.theirs + 1) - (a.mine + 1) / (a.theirs + 1))[0] ?? null;
}
function punchLine(c, x) {
  if (!x) return "";
  const other = c.name(c.other(x.side));
  return `${c.name(x.side)} has said “${x.w}” ${int(x.mine)} times. ${other}, ${x.theirs ? int(x.theirs) : "never"}.`;
}

export function wordsContent(c, off = new Set()) {
  const pools = wordPools(c);
  if (pools.A.length < 2 || pools.B.length < 2) return null;
  const shown = chooseWords(pools, off);
  const punch = punchWord(c, shown);
  return {
    kind: "words",
    title: "Who says what",
    left: c.name(c.sides[0]),
    right: c.name(c.sides[1]),
    cols: c.sides.map((side) => shown[side].map((x) => ({
      w: x.w,
      note: `${int(x.mine)} times · ${c.name(c.other(side))} ${int(x.theirs)}`.toUpperCase(),
      accent: Boolean(punch && x.key === punch.key),
    }))),
    lines: punch ? [punchLine(c, punch)] : [],
    chips: c.sides.map((side) => ({
      label: c.name(side),
      items: chipsOf(pools[side].filter((x) => off.has(x.key) || shown[side].includes(x)).map((x) => ({ key: x.key, text: x.w })), off),
    })),
    credits: totalsCredits(c),
    fileName: "love-language-model-words",
  };
}

// ---- the cast
// The old archetypes ("THE GHOST", chosen by a score) are gone. A role here is one counted behaviour,
// given to whoever did it more often, and printed with both numbers. Listed in editorial order: the
// first three each person qualifies for are billed, the same number for both.
const ROLES = [
  { id: "makes_laugh", role: () => "gets the laugh",
    how: () => "A “haha”, “lol”, 😂 or similar in the other person’s reply, sent within two minutes." },
  { id: "initiator", role: () => "says hi first",
    how: (v, c) => `${c.name(v.win)} sent the first message of ${int(v.w)} of your ${int(v.w + v.l)} conversations. A conversation starts after four quiet hours.` },
  { id: "voice_notes", role: () => "sends the voice notes",
    how: () => "Lines the export marks as an audio attachment. Only iPhone exports include them." },
  { id: "double_texts", role: () => "sends the follow-up",
    how: () => "A second message sent ten minutes or more after your own last one, with no reply in between." },
  { id: "goodnight_ritual", role: () => "says goodnight",
    how: () => "Messages with “good night”, “gn”, “sweet dreams” and a few others." },
  // (no emoji roles: a canvas without a colour-emoji font draws them as boxes)
  { id: "reel_dealer", role: (v) => (v.reels ? "sends the reels" : "sends the links"),
    how: (v) => (v.reels ? "Messages with a link in them. Most were Instagram reels." : "Messages with a link in them.") },
  { id: "questions", role: () => "asks the questions", how: () => "Messages with a question mark in them." },
  { id: "last_word", role: () => "gets the last word", how: () => "Who sent the last message before four quiet hours." },
];
const MIN_RATIO = 1.3; // closer than this is a tie, not a role

function roleCounts(id, v) {
  if (id === "emoji_top") {
    if (v.a === v.b) return null;
    return { win: v.a > v.b ? "A" : "B", w: Math.max(v.a, v.b), l: Math.min(v.a, v.b) };
  }
  return { win: v.win, w: v.w, l: v.l };
}

export function castRoles(c) {
  const out = { A: [], B: [] };
  for (const r of ROLES) {
    const v = c.stats[r.id];
    const k = v && roleCounts(r.id, v);
    if (!k || (k.w + 1) / (k.l + 1) < MIN_RATIO) continue;
    out[k.win].push({ key: `role:${r.id}`, id: r.id, side: k.win, role: r.role(v), mine: k.w, theirs: k.l, how: r.how(v, c) });
  }
  return out;
}
const billed = (roles) => Math.min(3, Math.max(1, Math.min(roles.A.length, roles.B.length)));

export function castContent(c, off = new Set()) {
  const roles = castRoles(c);
  if (!roles.A.length && !roles.B.length) return null;
  const n = billed(roles);
  const shown = { A: roles.A.filter((r) => !off.has(r.key)).slice(0, n), B: roles.B.filter((r) => !off.has(r.key)).slice(0, n) };
  const pet = c.stats.pet_name;
  const rt = c.stats.runtime_typing;
  const peak = c.stats.peak_hour;
  const extras = [];
  if (pet) extras.push({ key: "extra:pet", text: `“${pet.token}”` });
  if (rt && rt.hours >= 1) extras.push({ key: "extra:runtime", text: "Running time" });
  if (peak) extras.push({ key: "extra:peak", text: "Busiest hour" });
  const has = (k) => extras.some((e) => e.key === k) && !off.has(k);
  return {
    kind: "cast",
    names: `${c.name("A")} & ${c.name("B")}`,
    people: c.sides.map((side) => ({
      name: c.name(side),
      roles: shown[side].map((r) => ({ role: r.role, value: int(r.mine), note: `${c.name(c.other(side))} ${int(r.theirs)}`.toUpperCase() })),
    })),
    pet: has("extra:pet") ? { token: pet.token, line: `${int(pet.n)} times. ${c.name("A")} ${int(pet.a)}, ${c.name("B")} ${int(pet.b)}.` } : null,
    credits: [
      has("extra:runtime") ? `RUNNING TIME: ABOUT ${int(rt.hours)} HOURS OF TYPING` : null,
      has("extra:peak") ? `BUSIEST HOUR: ${peak.hour_label}` : null,
      `${shortDate(c.first)} – ${shortDate(c.last)}`.toUpperCase(),
    ].filter(Boolean),
    chips: [
      ...c.sides.map((side) => ({
        label: c.name(side),
        items: chipsOf(roles[side].filter((r) => off.has(r.key) || shown[side].includes(r)).map((r) => ({ key: r.key, text: r.role })), off),
      })),
      { label: "Also", items: chipsOf(extras, off) },
    ],
    fileName: "love-language-model-cast",
  };
}

// ---- the hour (grafted from candidates 2 and 3: every candidate surfaced the busiest hour)
// The 24 hours of your day, from every message's timestamp, with the busiest one in red. The title is the
// hour itself; the lines say how much of the chat it holds, and how much happened after midnight.
export function hourContent(c, off = new Set()) {
  const peak = c.stats.peak_hour;
  const hours = c.data.charts?.hours;
  if (!peak || !hours?.A || !hours?.B) return null;
  const totals = hours.A.map((a, i) => a + (hours.B[i] || 0));
  if (totals.reduce((x, y) => x + y, 0) === 0) return null;
  const night = c.stats.night_owl_share;
  const items = [{ key: "line:peak", chip: `${peak.hour_label} share`, text: `${capital(aboutShare(peak.pct))} of all your messages.` }]; // short and parallel: both lines print at full size
  if (night && night.pct >= 20) items.push({ key: "line:night", chip: "After midnight", text: `${capital(aboutShare(night.pct))}, between midnight and 5 AM.` });
  return {
    kind: "hour",
    kicker: "Your busiest hour",
    title: peak.hour_label,
    left: c.name(c.sides[0]),
    right: c.name(c.sides[1]),
    totals,
    peak: peak.hour,
    lines: items.filter((i) => !off.has(i.key)).map((i) => i.text),
    chips: [{ label: "Lines", items: chipsOf(items, off) }],
    credits: totalsCredits(c),
    fileName: "love-language-model-hour",
  };
}

// --------------------------------------------------------------- the receipts
const pair = (c, v) => `${c.name(v.win)} ${int(v.w)}, ${c.name(c.other(v.win))} ${int(v.l)}.`;
function aboutShare(pct) {
  if (pct >= 9.5 && pct < 11) return "one in ten";
  if (pct >= 31 && pct <= 36) return "a third";
  if (pct >= 23 && pct <= 27) return "a quarter";
  if (pct >= 48 && pct <= 52) return "half";
  return `${Math.round(pct)} in a hundred`;
}
const TYPING_HOW = (c) => {
  const words = c.stats.words_total_books?.words;
  return `${words ? `About ${int(words)} words, typed` : "Every word you typed,"} at 36 words a minute: an average phone typing speed, from a study of 37,000 people. An estimate.`;
};
const ALSO = {
  message_milestones: (v, c) => (v.q ? {
    label: `Message ${int(v.n)}`,
    text: `${longDate(v.date)}, from ${c.name(v.win)}: “${v.q}”`,
    how: `We counted every message from the first one and stopped at number ${int(v.n)}.`,
  } : null),
  longest_streak: (v) => ({
    label: "Longest streak",
    text: `${int(v.n)} days in a row, ${longDate(v.start)} to ${longDate(v.end)}.`,
    how: "Days on which both of you sent at least one message, one after another. A day ends at 5 AM.",
  }),
  longest_silence: (v, c) => ({
    label: "Longest quiet",
    text: `${capital(word(v.d))} days without a message, ${longDate(v.start)} to ${longDate(v.end)}. ${c.name(v.win)} wrote first.`,
    how: "The biggest gap between two messages, in whole empty days. We can’t tell you why.",
  }),
  peak_hour: (v) => ({
    label: "Busiest hour",
    text: `${v.hour_label}. About ${aboutShare(v.pct)} of your messages ${aboutShare(v.pct).startsWith("one in") ? "was" : "were"} sent in that hour.`,
    how: "Every message sorted by the hour on its timestamp.",
  }),
  night_owl_share: (v) => ({
    label: "After midnight",
    text: `About ${aboutShare(v.pct)} of your messages were sent between midnight and 5 AM.`,
    how: "Every message sorted by the hour on its timestamp.",
  }),
  pet_name: (v, c) => ({
    label: "Pet name",
    text: `“${v.token}”, ${int(v.n)} times. ${c.name("A")} ${int(v.a)}, ${c.name("B")} ${int(v.b)}.`,
    how: "The word that most often follows “love you”, “good morning” or “hi”, counted as a whole word.",
  }),
  runtime_typing: (v, c) => ({
    label: "Running time",
    text: `About ${int(v.hours)} hours of typing.`,
    how: TYPING_HOW(c),
  }),
  ok_period: (v, c) => ({
    label: "“ok.”",
    text: `With a full stop: ${pair(c, v)}`,
    how: "Messages that are exactly “ok.” or “okay.”. We can’t hear the tone.",
  }),
  double_texts: (v, c) => ({
    label: "Double texts",
    text: pair(c, v),
    how: "A follow-up sent ten minutes or more after your own last message, with no reply in between.",
  }),
  emoji_top: (v, c) => {
    const each = c.stats.emoji_per_person;
    const both = each && each.top_a === v.emoji && each.top_b === v.emoji;
    return {
      label: "Top emoji",
      text: `${v.emoji}, ${int(v.n)} times. ${c.name("A")} ${int(v.a)}, ${c.name("B")} ${int(v.b)}.${both ? " It is each of your own favourite, too." : ""}`,
      how: "Every emoji in every message, counted one by one.",
    };
  },
  voice_notes: (v, c) => ({
    label: "Voice notes",
    text: pair(c, v),
    how: "Lines the export marks as an audio attachment. Only iPhone exports include them.",
  }),
  initiator: (v, c) => ({
    label: "Who starts the conversation",
    text: `${c.name(v.win)} ${int(v.w)} times, ${c.name(c.other(v.win))} ${int(v.l)}.`,
    how: "A conversation starts with the first message after four quiet hours.",
  }),
  makes_laugh: (v, c) => ({
    label: "Who gets the laugh",
    text: `${c.name(v.win)} made ${c.name(c.other(v.win))} laugh ${int(v.w)} times; the other way round, ${int(v.l)}.`,
    how: "A “haha”, “lol”, 😂 or similar sent within two minutes of the other person’s message. A real laugh is invisible to us.",
  }),
  goodnight_ritual: (v, c) => ({
    label: "Goodnights",
    text: pair(c, v),
    how: "Messages with “good night”, “gn”, “sweet dreams” and a few others.",
  }),
  reel_dealer: (v, c) => ({
    label: v.reels ? "Reels and links" : "Links",
    text: pair(c, v),
    how: v.reels ? "Messages with a link in them. Most were Instagram reels." : "Messages with a link in them.",
  }),
  questions: (v, c) => ({
    label: "Questions",
    text: pair(c, v),
    how: "Messages with a question mark in them.",
  }),
  last_word: (v, c) => ({
    label: "The last word",
    text: pair(c, v),
    how: "Who sent the last message before four quiet hours.",
  }),
  affection_count: (v, c) => ({
    label: "Affectionate messages",
    text: pair(c, v),
    how: "Messages with a phrase like “love you” or “miss you”, a pet name or a heart emoji. Every pet name counts, so a habit looks like affection. It counts words, not feelings.",
  }),
  message_share: (v, c) => ({
    label: "Messages each",
    text: pair(c, v),
    how: "Every message, photos and voice notes included. WhatsApp’s own notices don’t count.",
  }),
  msgs_per_day: (v, c) => ({
    label: "A normal pace",
    text: `About ${int(v.n)} messages a day, over ${int(daysBetween(c.first, c.last))} days.`,
    how: "All your messages divided by the days between the first and the last.",
  }),
  words_total_books: (v) => ({
    label: "Words",
    text: `About ${int(v.words)}, roughly ${word(Math.round(v.x))} copies of ${v.book}.`,
    how: "Words in text messages, compared with the length of the book.",
  }),
  deleted: (v, c) => ({
    label: "Deleted messages",
    text: pair(c, v),
    how: "Messages WhatsApp shows as deleted. We can’t see what they said either.",
  }),
  swearing: (v, c) => ({
    label: "Swear words",
    text: `${int(v.n)}${c.stats.words_total_books ? `, in about ${int(c.stats.words_total_books.words)} words` : ""}.`,
    how: "Matched against a short list of English and Hindi swear words. We never print the list.",
  }),
};
const ALSO_ORDER = ["message_milestones", "longest_streak", "longest_silence", "peak_hour", "night_owl_share", "pet_name",
  "runtime_typing", "ok_period", "double_texts", "emoji_top", "voice_notes", "initiator", "makes_laugh", "goodnight_ritual",
  "reel_dealer", "questions", "last_word", "message_share", "msgs_per_day", "words_total_books", "deleted",
  "swearing"];

export function receipts(c, facts) {
  const used = new Set(facts.map((f) => f.id));
  if (facts.some((f) => f.visual?.kind === "gap")) used.add("longest_silence"); // the busiest day already told it
  const story = facts.map((f) => ({ label: f.label || f.kicker, text: f.plain ?? plainFact(f), how: f.how }));

  // What the two new cards print, each with its own how (the poster's lines are already in the story).
  const cards = [];
  if (!used.has("words")) {
    const w = chooseWords(wordPools(c));
    if (w.A.length >= 2 && w.B.length >= 2) {
      cards.push({ label: "Who says what", text: `${c.name("A")}: ${w.A.map((x) => x.w).join(", ")}. ${c.name("B")}: ${w.B.map((x) => x.w).join(", ")}.`, how: WORDS_HOW });
    }
  }
  const roles = castRoles(c);
  const n = billed(roles);
  for (const side of c.sides) {
    for (const r of roles[side].slice(0, n)) {
      cards.push({ label: `${c.name(side)} ${r.role}`, text: `${int(r.mine)} times. ${c.name(c.other(side))}, ${int(r.theirs)}.`, how: r.how });
      used.add(r.id);
    }
  }
  for (const id of ["pet_name", "runtime_typing", "peak_hour"]) {
    if (used.has(id) || !c.stats[id]) continue;
    const item = ALSO[id](c.stats[id], c);
    if (id === "pet_name") item.label = "And introducing: your pet name";
    cards.push(item);
    used.add(id);
  }

  const also = ALSO_ORDER.filter((id) => !used.has(id) && c.stats[id]).map((id) => ALSO[id](c.stats[id], c)).filter(Boolean);
  return {
    sections: [
      { title: "In your story", items: story },
      { title: "On your cards", items: cards },
      { title: "Also counted", items: also },
    ],
    limits: [
      "We count words, not feelings. An “ok.” can be a perfectly happy one.",
      "Words are matched by spelling. Sarcasm, other languages and creative spelling can slip past.",
      "We only see this one chat. Not calls, not other apps, not the time you spend together.",
      "Typical reply times use the middle value, so one slow night doesn’t skew them.",
      "Your chat was read on this device. Nothing was uploaded or kept.",
    ],
  };
}

function plainFact(f) {
  if (f.rows) return `${f.rows.map((r) => `${r.name} ${r.value}`).join(", ")}. ${f.line}`;
  return `${f.big}. ${f.line}`.replace(/([.?!”])\. /, "$1 ").replace(/ /g, " ");
}
