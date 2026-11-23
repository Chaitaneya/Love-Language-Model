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
  return { data, stats, names, name: (side) => names[side], other, first: data.meta.range[0], last: data.meta.range[1] };
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
      kicker: `${shortDate(v.start)} to ${shortDate(v.end)}`,
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
      const v = c.stats[id];
      const fact = v ? REVEAL[id](v, c) : null;
      if (fact) {
        out.push(fact);
        break;
      }
    }
  }
  return out;
}

// ----------------------------------------------------------------- the poster
export function posterContent(c) {
  const m = c.stats.longest_monologue;
  const ily = c.stats.first_ily;
  const run = m && m.n >= 12 ? m : null;
  const titles = [];
  if (run && run.q && run.q.length <= 8) titles.push({ key: "word", text: run.q });
  titles.push({ key: "names", text: `${c.name("A")} & ${c.name("B")}` });

  const lines = [];
  if (run) lines.push(`${c.name(run.win)} sent ${int(run.n)} messages in a row.`);
  if (ily) lines.push(`${c.name(ily.win)} said ‘I love you’ first.`);

  return {
    titles,
    monologue: run ? { n: run.n, lens: run.lens || [] } : null,
    left: run ? c.name(c.other(run.win)) : c.name("B"),
    right: run ? c.name(run.win) : c.name("A"),
    lines,
    credits: [
      `${int(c.data.meta.messages)} messages · ${int(daysBetween(c.first, c.last))} days`.toUpperCase(),
      `${shortDate(c.first)} – ${shortDate(c.last)}`.toUpperCase(),
    ],
    fileName: "love-language-model-poster", // deliberately no names in the file name
  };
}

// --------------------------------------------------------------- the receipts
const pair = (c, v) => `${c.name(v.win)} ${int(v.w)}, ${c.name(c.other(v.win))} ${int(v.l)}.`;
const ALSO = {
  peak_hour: (v) => ({
    label: "Busiest hour",
    text: `${v.hour_label}. About ${v.pct >= 9.5 && v.pct < 11 ? "one in ten" : `${Math.round(v.pct)} in a hundred`} of your messages were sent in that hour.`,
    how: "Every message sorted by the hour on its timestamp.",
  }),
  longest_streak: (v) => ({
    label: "Longest streak",
    text: `${int(v.n)} days in a row, ${shortDate(v.start)} to ${shortDate(v.end)}.`,
    how: "Days on which both of you sent at least one message, one after another. A day ends at 5 AM.",
  }),
  pet_name: (v, c) => ({
    label: "Pet name",
    text: `“${v.token}”, ${int(v.n)} times. ${c.name("A")} ${int(v.a)}, ${c.name("B")} ${int(v.b)}.`,
    how: "The word that most often follows “love you”, “good morning” or “hi”, counted as a whole word.",
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
  emoji_top: (v, c) => ({
    label: "Top emoji",
    text: `${v.emoji}, ${int(v.n)} times. ${c.name("A")} ${int(v.a)}, ${c.name("B")} ${int(v.b)}.`,
    how: "Every emoji in every message, counted one by one.",
  }),
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
  words_total_books: (v) => ({
    label: "Words",
    text: `About ${int(v.words)}, roughly ${word(Math.round(v.x))} copies of ${v.book}.`,
    how: "Words in text messages, compared with the length of the book.",
  }),
};
const ALSO_ORDER = ["peak_hour", "longest_streak", "pet_name", "ok_period", "double_texts", "emoji_top", "voice_notes",
  "initiator", "makes_laugh", "goodnight_ritual", "affection_count", "message_share", "words_total_books"];

export function receipts(c, facts) {
  const shown = new Set(facts.map((f) => f.id));
  const story = facts.map((f) => ({ label: f.label || f.kicker, text: plainFact(f), how: f.how }));
  const also = ALSO_ORDER.filter((id) => !shown.has(id) && c.stats[id]).map((id) => ALSO[id](c.stats[id], c));
  return {
    sections: [
      { title: "In your highlights", items: story },
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
  return `${f.big}. ${f.line}`.replace(/([.?!”])\. /, "$1 ").replace(/ /g, " ");
}
