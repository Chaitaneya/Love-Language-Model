// The flow: landing → add your chat → names → highlights → poster, plus two sheets one level deeper
// (how we counted; how it works). No framework: each screen is a <section> and show() swaps them.
// Browser Back works at every step (one history entry per screen). docs/decision.md D45.
import "./style.css";
import { createEngine } from "./engine.js";
import { createPrivacy } from "./privacy.js";
import { explain, dateOrderQuestion } from "./errors.js";
import { loadFonts } from "./fonts.js";
import { makeContext, pickFacts, posterContent, receipts, int } from "./facts.js";
import { drawPoster, preparePhoto } from "./poster.js";
import { createReveal } from "./reveal.js";
import { createSheet } from "./sheet.js";
import { reducedMotion } from "./spring.js";

// For anyone who opens DevTools to check the privacy claim (the intended audience).
console.info(
  "%cLove Language Model%c\nYou opened DevTools to check. Good. Open the Network tab, add a chat, and watch it stay empty: "
  + "the counting runs here, in this tab, and there is no server to send anything to. “How it works” at the bottom counts the requests for you.",
  "font: 600 15px system-ui; color: #f0634c", "font: 13px system-ui");

const DEMO_CHAT = new URL("demo/demo_chat.txt", document.baseURI).href;
const DEMO_RESULT = new URL("demo/demo-result.json", document.baseURI).href; // only for the landing picture
const MAX_BYTES = 150 * 1024 * 1024;
const ORDER = ["landing", "add", "names", "reveal", "poster"];
const ANALYZE = { seed: 1234, spicy: false, quotes: true };

const state = {
  result: null, summary: null, names: { A: "", B: "" }, facts: [], poster: null, title: 0, photo: null,
  current: "landing", timings: {},
};

const $ = (id) => document.getElementById(id);
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

// Python starts loading the moment the page opens, and the fonts with it. Both are fully loaded before
// a chat is read, so "0 requests since your chat was in memory" is true by construction (D33, D37).
const engine = createEngine();
const privacy = createPrivacy(engine);
const fontsReady = loadFonts();
engine.init().then(
  () => { document.documentElement.dataset.engine = "ready"; }, // for tests and the curious; nothing on screen
  (err) => console.error(err),
);

// ------------------------------------------------------------------ screens and history
function show(name, { push = true } = {}) {
  const from = state.current;
  if (from === name) return;
  const forward = ORDER.indexOf(name) > ORDER.indexOf(from);
  const into = $(name);
  $(from).hidden = true;
  into.hidden = false;
  into.classList.remove("enter-forward", "enter-back");
  void into.offsetWidth; // restart the entrance
  into.classList.add(forward ? "enter-forward" : "enter-back");
  state.current = name;
  if (push) history.pushState({ screen: name }, "");
  window.scrollTo(0, 0);
  if (from === "reveal") reveal.stop();
  if (from === "add") cancelLoading();
  if (name === "reveal") reveal.start(forward ? 0 : Math.max(0, state.facts.length - 1));
  const heading = into.querySelector('[tabindex="-1"]:not(input)');
  if (heading) heading.focus({ preventScroll: true });
  else into.querySelector("button, input")?.focus({ preventScroll: true });
}
history.replaceState({ screen: "landing" }, "");
window.addEventListener("popstate", (e) => {
  let to = e.state?.screen ?? "landing";
  if (!state.result && ["names", "reveal", "poster"].includes(to)) to = "landing"; // nothing to show any more
  show(to, { push: false });
});
document.querySelectorAll("[data-back]").forEach((b) => b.addEventListener("click", () => history.back()));

// ------------------------------------------------------------------ landing
// The example poster on the landing page is drawn from a precomputed demo result (made at build time by
// the same core), so it appears at once, before Python has even started.
Promise.all([fetch(DEMO_RESULT).then((r) => r.json()), fontsReady]).then(([data]) => {
  const c = makeContext(data, { A: data.people.A.name, B: data.people.B.name });
  const full = document.createElement("canvas");
  drawPoster(full, posterContent(c));
  const preview = $("preview-canvas");
  const w = Math.round((preview.clientWidth || 300) * Math.min(window.devicePixelRatio || 1, 2));
  preview.width = w;
  preview.height = Math.round((w * 16) / 9);
  const g = preview.getContext("2d");
  g.imageSmoothingQuality = "high";
  g.drawImage(full, 0, 0, preview.width, preview.height);
  $("preview-caption").textContent = `${c.name("A")} & ${c.name("B")}, a demo couple`;
}).catch(() => { $("preview-caption").textContent = ""; });

$("go-add").addEventListener("click", () => show("add"));
$("go-demo").addEventListener("click", () => { show("add"); useDemo(); });

// ------------------------------------------------------------------ add your chat
const fileInput = $("chat-file");
const drop = $("drop");
if (window.matchMedia("(pointer: fine)").matches) $("drop-sub").textContent = "A .zip or .txt from WhatsApp, or drop it here";

function useFile(file) {
  if (!file) return;
  if (file.size > MAX_BYTES) {
    return openDialog({ title: "That file is enormous.", body: "Chat exports without media are a few megabytes at most. Is it really a WhatsApp export?" });
  }
  runLoad(() => file.arrayBuffer());
}
const useDemo = () => runLoad(async () => (await fetch(DEMO_CHAT)).arrayBuffer());

fileInput.addEventListener("change", () => { useFile(fileInput.files[0]); fileInput.value = ""; });
drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("is-over"); });
drop.addEventListener("dragleave", () => drop.classList.remove("is-over"));
drop.addEventListener("drop", (e) => { e.preventDefault(); drop.classList.remove("is-over"); useFile(e.dataTransfer.files[0]); });
for (const ev of ["dragover", "drop"]) window.addEventListener(ev, (e) => e.preventDefault()); // a miss must not open the file
$("add-demo").addEventListener("click", useDemo);

const LOADING_LINES = ["Reading your chat", "Counting replies", "Picking the moments"];
let loadingTimers = [];
let loadToken = 0; // every run gets a number; a run that was cancelled (Back) or replaced is ignored when it lands

function setLoading(on) {
  $("add-choose").hidden = on;
  $("add-loading").hidden = !on;
  loadingTimers.forEach(clearTimeout);
  loadingTimers = [];
  if (!on) return;
  const line = $("loading-line");
  line.textContent = LOADING_LINES[0];
  loadingTimers = [
    setTimeout(() => { line.textContent = LOADING_LINES[1]; }, 1200),
    setTimeout(() => { line.textContent = LOADING_LINES[2]; }, 2600),
  ];
}
function cancelLoading() {
  loadToken++;
  setLoading(false);
}

async function runLoad(getBytes, dateOrder = null) {
  const token = ++loadToken;
  setLoading(true);
  const stale = () => token !== loadToken;
  try {
    await Promise.all([engine.init(), fontsReady]);
    const bytes = await getBytes();
    if (stale()) return;
    await privacy.mark(); // from here on, any network request would show up in "How it works"
    const loaded = await engine.load(bytes, dateOrder);
    if (stale()) return;
    if (!loaded.ok) return fail(loaded.error, getBytes);
    state.timings.load = loaded.ms;
    const analyzed = await engine.analyze(ANALYZE);
    if (stale()) return;
    if (!analyzed.ok) return fail(analyzed.error, getBytes);
    state.timings.analyze = analyzed.ms;
    state.summary = loaded.summary;
    state.result = analyzed.result;
    state.names = { A: state.result.people.A.name, B: state.result.people.B.name };
    fillNames();
    loadToken++; // done: nothing else may land
    setLoading(false);
    show("names");
  } catch (err) {
    if (!stale()) fail({ code: "internal", message: err.message }, getBytes);
  }
}

function fail(error, getBytes) {
  setLoading(false);
  if (error.code === "date_order_ambiguous") {
    const q = dateOrderQuestion(error);
    if (q) {
      return openDialog({
        title: "One question about the dates", body: q.text,
        actions: [
          { label: q.dmy, primary: true, onClick: () => runLoad(getBytes, "DMY") },
          { label: q.mdy, onClick: () => runLoad(getBytes, "MDY") },
        ],
      });
    }
  }
  const msg = explain(error);
  openDialog({ title: msg.title, body: msg.body, technical: msg.technical, actions: [{ label: "Choose another file", primary: true }] });
}

function openDialog({ title, body, technical, actions = [{ label: "OK", primary: true }] }) {
  const dlg = $("dialog");
  $("dialog-title").textContent = title;
  $("dialog-body").textContent = body;
  $("dialog-tech").hidden = !technical;
  $("dialog-pre").textContent = technical ?? "";
  $("dialog-actions").replaceChildren(...actions.map((a) => {
    const b = el("button", a.primary ? "btn btn-primary" : "btn btn-secondary", a.label);
    b.type = "button";
    b.addEventListener("click", () => { dlg.close(); a.onClick?.(); });
    return b;
  }));
  if (dlg.open) dlg.close();
  dlg.showModal();
}

// ------------------------------------------------------------------- names
function fillNames() {
  const [first, second] = state.summary?.people ?? [state.names.A, state.names.B];
  const counts = state.summary?.counts ?? {};
  $("name-a").value = state.names.A;
  $("name-b").value = state.names.B;
  $("name-a-label").textContent = counts[first] != null ? `Sent ${int(counts[first])} messages` : "First person";
  $("name-b-label").textContent = counts[second] != null ? `Sent ${int(counts[second])} messages` : "Second person";
}

$("names-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const clean = (v, fallback) => v.trim().replace(/\s+/g, " ").slice(0, 18) || fallback;
  state.names = {
    A: clean($("name-a").value, state.result.people.A.name),
    B: clean($("name-b").value, state.result.people.B.name),
  };
  build();
  show("reveal");
});

function build() {
  const c = makeContext(state.result, state.names);
  state.facts = pickFacts(c);
  state.poster = posterContent(c);
  state.title = 0;
  reveal.load(state.facts);
  state.receipts = receipts(c, state.facts);
  renderTitleChoice();
  redraw();
}

// ------------------------------------------------------------------ reveal
const reveal = createReveal({ onDone: () => show("poster") });
$("skip").addEventListener("click", () => show("poster"));

// ------------------------------------------------------------------ poster
const canvas = $("poster-canvas");

function redraw() {
  drawPoster(canvas, state.poster, { title: state.title, photo: state.photo });
  const t = state.poster.titles[state.title].text;
  canvas.setAttribute("aria-label", `Poster titled ${t}. ${state.poster.lines.join(" ")}`);
}

function renderTitleChoice() {
  const group = $("title-choice");
  const buttons = state.poster.titles.map((t, i) => {
    const b = el("button", "seg-btn", t.key === "word" ? `“${t.text}”` : t.text);
    b.type = "button";
    b.setAttribute("role", "radio");
    b.setAttribute("aria-checked", String(i === state.title));
    b.tabIndex = i === state.title ? 0 : -1;
    b.addEventListener("click", () => chooseTitle(i));
    b.addEventListener("keydown", (e) => {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      e.preventDefault();
      const n = state.poster.titles.length;
      const j = (state.title + (e.key === "ArrowRight" ? 1 : -1) + n) % n;
      chooseTitle(j);
      group.querySelectorAll(".seg-btn")[j].focus();
    });
    return b;
  });
  const label = el("span", "seg-label", "Title");
  label.setAttribute("aria-hidden", "true");
  group.replaceChildren(label, ...buttons);
  group.hidden = buttons.length < 2;
}

function chooseTitle(i) {
  state.title = i;
  [...$("title-choice").querySelectorAll(".seg-btn")].forEach((b, k) => {
    b.setAttribute("aria-checked", String(k === i));
    b.tabIndex = k === i ? 0 : -1;
  });
  redraw();
}

const photoInput = $("photo-file");
$("photo-btn").addEventListener("click", () => {
  if (state.photo) {
    state.photo = null;
    $("photo-btn").textContent = "Add a photo";
    setStatus("Photo removed.");
    redraw();
    return;
  }
  photoInput.click();
});

photoInput.addEventListener("change", async () => {
  const file = photoInput.files[0];
  photoInput.value = "";
  if (!file) return;
  try {
    let bitmap;
    try { bitmap = await createImageBitmap(file, { imageOrientation: "from-image" }); } catch { bitmap = await createImageBitmap(file); }
    state.photo = preparePhoto(bitmap); // the photo becomes a canvas here and never leaves the page
    bitmap.close();
    $("photo-btn").textContent = "Remove photo";
    setStatus("Photo added. It stays on this device.");
    redraw();
  } catch {
    setStatus("That file didn’t open as an image. Try a JPEG or PNG.");
  }
});

$("save-btn").addEventListener("click", () => {
  canvas.toBlob((blob) => {
    if (!blob) return setStatus("Couldn’t make the image. Try again.");
    const file = new File([blob], `${state.poster.fileName}.png`, { type: "image/png" });
    const touch = window.matchMedia("(pointer: coarse)").matches;
    if (touch && navigator.canShare?.({ files: [file] })) {
      navigator.share({ files: [file] }).catch(() => {});
      return;
    }
    const url = URL.createObjectURL(blob);
    const a = el("a");
    a.href = url;
    a.download = file.name;
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 20000);
    setStatus("Saved. It was made on this device.");
  }, "image/png");
});

let statusTimer = 0;
function setStatus(text) {
  const s = $("status");
  s.textContent = text;
  clearTimeout(statusTimer);
  statusTimer = setTimeout(() => { s.textContent = ""; }, 4000);
}

// "Start over" forgets everything: the worker that held the chat goes, and so does the page.
$("restart").addEventListener("click", async () => {
  await engine.burn();
  engine.terminate();
  location.replace(location.pathname);
});

// ---------------------------------------------------------------- one level deeper
const sheet = createSheet();
$("open-receipts").addEventListener("click", (e) => {
  showSheet("How we counted", receiptsBody(state.receipts));
  sheet.show(e.currentTarget);
});
$("open-how").addEventListener("click", async (e) => {
  showSheet("How it works", await howBody());
  sheet.show(e.currentTarget);
});

function showSheet(title, nodes) {
  $("sheet-title").textContent = title;
  $("sheet-body").replaceChildren(...nodes);
  $("sheet-body").scrollTop = 0;
}

function receiptsBody(r) {
  const nodes = [el("p", "sheet-intro", "Every number here was counted from the chat itself. Nothing is scored or weighted.")];
  for (const section of r.sections) {
    if (!section.items.length) continue;
    const sec = el("section", "receipt-group");
    sec.append(el("h3", "receipt-title", section.title));
    const list = el("ul", "receipt-list");
    for (const item of section.items) {
      const li = el("li", "receipt");
      li.append(el("p", "receipt-label", item.label), el("p", "receipt-text", item.text), el("p", "receipt-how", item.how));
      list.append(li);
    }
    sec.append(list);
    nodes.push(sec);
  }
  const limits = el("section", "receipt-group limits");
  limits.append(el("h3", "receipt-title", "What counting can’t tell you"));
  const ul = el("ul", "limit-list");
  r.limits.forEach((t) => ul.append(el("li", null, t)));
  limits.append(ul);
  nodes.push(limits);
  return nodes;
}

async function howBody() {
  const [after, before] = [await privacy.since(), await privacy.before()];
  const info = engine.info;
  const proof = el("div", "proof");
  const count = el("p", "proof-number", after == null ? "—" : String(after.length));
  count.id = "net-count";
  proof.append(count, el("p", "proof-label", after == null
    ? "Network requests since your chat was read. Add a chat and this stays at 0."
    : after.length === 0 ? "Network requests since your chat was read. Nothing left this page." : "Network requests since your chat was read:"));
  if (after?.length) {
    const ul = el("ul", "files");
    after.forEach((u) => ul.append(el("li", null, u)));
    proof.append(ul);
  }
  const steps = el("ol", "limit-list");
  for (const t of [
    "Your file is read inside this page and handed to a background worker. It is never sent to a server: there isn’t one.",
    "The worker runs a small Python program (no dependencies) on a WebAssembly build of Python, right here.",
    "It counts things: who writes first, how long replies take, which words each of you uses. Then it picks a few true moments.",
    "“Start over”, or closing the tab, throws everything away. Nothing is stored.",
  ]) steps.append(el("li", null, t));
  const row = (k, v) => { const tr = el("tr"); tr.append(el("th", null, k), el("td", null, v)); return tr; };
  const table = el("table", "engine");
  const tbody = el("tbody");
  tbody.append(
    row("Python", info ? `${info.python}, in WebAssembly (Pyodide ${info.pyodide})` : "starting…"),
    row("Started in", info ? `${int(info.ms)} ms` : "…"),
    row("Read the chat", state.timings.load != null ? `${int(state.timings.load)} ms` : "no chat yet"),
    row("Counted it", state.timings.analyze != null ? `${int(state.timings.analyze)} ms` : "no chat yet"));
  table.append(tbody);
  const files = el("details", "files");
  files.append(el("summary", null, `Everything this page loaded (${before.length} files, all from this site)`));
  const list = el("ul");
  before.forEach((u) => list.append(el("li", null, u)));
  files.append(list);
  return [proof, el("h3", "receipt-title", "How it works"), steps, el("h3", "receipt-title", "The engine"), table, files,
    el("p", "sheet-intro", "Don’t take our word for it: open your browser’s developer tools, go to Network, add a chat, and watch.")];
}

// Keep the reduced-motion class in sync for CSS that cannot use the media query alone.
function syncMotion() { document.documentElement.classList.toggle("reduce-motion", reducedMotion.matches); }
reducedMotion.addEventListener("change", syncMotion);
syncMotion();

// iOS Safari only applies :active (press feedback) when a touch listener exists.
document.addEventListener("touchstart", () => {}, { passive: true });
window.addEventListener("unhandledrejection", (e) => console.error(e.reason));

if (import.meta.env.DEV) window.__lm = { engine, state, privacy }; // dev-only handle for tests
