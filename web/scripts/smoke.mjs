// Headless check of the exact path the browser uses: Pyodide (WebAssembly) + the lovelm wheel + glue.py.
//   node scripts/smoke.mjs
// It proves (1) the wheel imports and runs under Pyodide's Python, (2) the result equals native CPython's
// (same JSON, so no platform float drift), (3) errors arrive coded, and (4) how long it all takes.
import { existsSync, readFileSync } from "node:fs";
import { isDeepStrictEqual } from "node:util";
import { spawnSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { loadPyodide } from "pyodide";

const web = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const root = resolve(web, "..");
const assets = JSON.parse(readFileSync(join(web, "public", "assets.json"), "utf8"));
const demo = readFileSync(join(root, "demo", "demo_chat.txt"));
const t = () => performance.now();
const ms = (a) => Math.round(t() - a);
let failures = 0;
const check = (ok, what, extra = "") => { console.log(`${ok ? "ok  " : "FAIL"} ${what}${extra ? "  " + extra : ""}`); if (!ok) failures++; };

let t0 = t();
const py = await loadPyodide();
console.log(`pyodide ${py.version}, python ${py.runPython("import sys; sys.version.split()[0]")}   boot ${ms(t0)} ms`);
t0 = t();
// Pyodide rejects Node Buffers (a Uint8Array subclass); the browser passes a plain ArrayBuffer
py.unpackArchive(new Uint8Array(readFileSync(join(web, "public", assets.wheel))), "wheel");
py.runPython(readFileSync(join(web, "src", "glue.py"), "utf8"));
console.log(`wheel + glue ready  ${ms(t0)} ms`);

const load = py.globals.get("load");
const analyze = py.globals.get("analyze");
const call = (fn, ...args) => JSON.parse(fn(...args));

t0 = t();
const loaded = call(load, new Uint8Array(demo), undefined);
check(loaded.ok && loaded.summary.messages === 47382, "load demo chat", `${ms(t0)} ms (python reports ${loaded.ms} ms)`);
check(JSON.stringify(loaded.summary.people) === '["Rohan","Tara"]', "participants detected", loaded.summary.people.join(", "));

const timings = [];
let plain, spicy;
for (let i = 0; i < 3; i++) { t0 = t(); plain = call(analyze, JSON.stringify({ seed: 1234 })); timings.push(ms(t0)); }
t0 = t(); spicy = call(analyze, JSON.stringify({ seed: 1234, spicy: true })); const spicyMs = ms(t0);
check(plain.ok && plain.result.poster.title.text === "2 AM AND STILL TYPING", "poster title", plain.result?.poster.title.text);
check(plain.result.poster.rating.text === '[PG] for 2,341 😭, excessive use of "babu" and 38 passive-aggressive "ok."s', "rating line");
check(spicy.result.poster.title.text === "SORRY 214", "spicy title", spicy.result.poster.title.text);
console.log(`analyze (47,382 messages): ${timings.join(", ")} ms plain, ${spicyMs} ms spicy   [CPython 3.13 native: ~1100 ms]`);

// the browser and native CPython must agree to the byte on everything the UI shows
// the project venv when there is one (a laptop), otherwise the system python3 (CI has no venv)
const nativePython = [join(root, ".venv", "bin", "python"), "python3"].find((p) => p === "python3" || existsSync(p));
const native = spawnSync(nativePython, ["-I", "-c", `
import sys, json
sys.path.insert(0, "${join(root, "core")}")
from lovelm.api import load_chat, analyze
r = analyze(load_chat(open("${join(root, "demo", "demo_chat.txt")}", "rb").read()), seed=1234)
print(json.dumps(r, ensure_ascii=False, separators=(",", ":")))`], { encoding: "utf8", maxBuffer: 1 << 28 });
if (native.status !== 0 || !native.stdout) {
  console.log(`FAIL native CPython run (${nativePython}): ${native.error?.message || native.stderr.trim().split("\n").pop()}`);
  process.exit(1);
}
// compare parsed values: JSON text differs harmlessly ("1.0" vs "1"), the data must not
const nativeResult = JSON.parse(native.stdout);
const same = isDeepStrictEqual(plain.result, nativeResult);
check(same, "Pyodide result is identical to native CPython", `${native.stdout.length.toLocaleString()} chars`);
if (!same) {
  const walk = (x, y, path) => {
    if (isDeepStrictEqual(x, y)) return false;
    if (x && y && typeof x === "object" && typeof y === "object") {
      for (const k of new Set([...Object.keys(x), ...Object.keys(y)])) if (walk(x[k], y[k], `${path}.${k}`)) return true;
      return true;
    }
    console.log("  differs at", path, ":", JSON.stringify(x), "vs", JSON.stringify(y));
    return true;
  };
  walk(plain.result, nativeResult, "result");
}

// errors are coded, not stack traces
for (const [name, bytes, code] of [
  ["garbage", new TextEncoder().encode("hello\nthis is not a chat\n"), "unrecognized_format"],
  ["trailer", new TextEncoder().encode(Array.from({ length: 10 }, (_, i) => `13/01/24, 10:0${i} am - ${i % 2 ? "Bo" : "Ann"}: hi`).join("\n")), "too_few_messages"],
  ["group chat", new TextEncoder().encode(Array.from({ length: 400 }, (_, i) => `13/01/24, 10:${String(i % 60).padStart(2, "0")} am - ${["A", "B", "C"][i % 3]}: hi`).join("\n")), "not_two_people"],
]) {
  const r = call(load, bytes, undefined);
  check(!r.ok && r.error.code === code, `error: ${name}`, r.ok ? "(no error!)" : `${r.error.code}: ${r.error.message}`);
}
const noChat = call(analyze, "{}");
check(!noChat.ok && noChat.error.code === "no_chat", "analyze without a chat is a coded error");
const amb = call(load, new TextEncoder().encode("03/04/24, 10:00 am - Ann: hi\n05/04/24, 10:00 am - Bo: yo\n07/04/24, 10:00 am - Ann: hey\n"), undefined);
check(!amb.ok && amb.error.code === "date_order_ambiguous" && amb.error.data.as_dmy === "2024-04-03", "ambiguous dates asks the user", JSON.stringify(amb.error?.data));
check(call(py.globals.get("burn")).ok, "burn");
console.log(failures ? `\n${failures} check(s) FAILED` : "\nall smoke checks passed");
process.exit(failures ? 1 : 0);
