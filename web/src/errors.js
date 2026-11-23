// What to say when the core refuses a file. The core returns a stable `code`; the voice lives here.
// Pure functions: unit-tested in test/errors.test.mjs.

export function explain(error) {
  const d = error?.data ?? {};
  switch (error?.code) {
    case "too_few_messages":
      return {
        title: "This isn't a movie, it's a trailer.",
        body: `That chat has ${d.count ?? "very few"} messages. We need at least 300 to say anything with a straight face. Come back with more messages.`,
      };
    case "not_two_people": {
      const n = Array.isArray(d.names) ? d.names.length : "Too many";
      return {
        title: `${n} people? That's not a couple, that's a cast.`,
        body: "Group chats aren't supported: this is a two-person game. Export a one-to-one chat instead.",
      };
    }
    case "unrecognized_format":
      return {
        title: "We couldn't read that file.",
        body: "Is it a WhatsApp export? In WhatsApp: open the chat → ⋮ (or the contact name) → Export chat → Without media. iPhone gives you a .zip, Android a .txt: both work.",
      };
    case "bad_archive":
      return {
        title: "That zip didn't open.",
        body: d.size ? "The chat file inside is enormous. Is it really a WhatsApp export?" : "We couldn't find a chat inside it. Export again with “Without media”.",
      };
    case "inconsistent_dates":
      return {
        title: "The dates in that file contradict themselves.",
        body: "Some dates only make sense day-first and others only month-first. If you edited the file, undo that; otherwise export it again.",
      };
    case "no_chat":
      return { title: "No chat is loaded.", body: "Pick a file first." };
    default:
      return {
        title: "Something broke on our side.",
        body: "Nothing was sent anywhere: your chat is still only in this tab. Reload and try again; if it keeps happening, the technical note below will help.",
        technical: error?.message,
      };
  }
}

/** The question asked when dates could be day-first or month-first and the file does not say. */
export function dateOrderQuestion(error) {
  const d = error?.data ?? {};
  if (!d.sample) return null;
  const [a, b, y] = d.sample;
  const pad = (n) => String(n).padStart(2, "0");
  return {
    text: `Is ${pad(a)}/${pad(b)}/${pad(y % 100)} the ${ordinal(a)} of ${monthName(b)} or ${monthName(a)} ${ordinal(b)}?`,
    dmy: `${ordinal(a)} of ${monthName(b)}`,
    mdy: `${monthName(a)} ${ordinal(b)}`,
  };
}

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const monthName = (n) => MONTHS[n - 1] ?? String(n);
export function ordinal(n) {
  const s = ["th", "st", "nd", "rd"], v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}
