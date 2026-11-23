// Copies everything the page needs into public/ so the site is fully self-hosted:
//   public/pyodide/*          Pyodide runtime (no CDN, so "nothing leaves this tab" is checkable)
//   public/wheels/*.whl       the lovelm core, built from ../core as a pure-Python wheel
//   public/demo/demo_chat.txt the demo couple
//   public/demo/demo-result.json the demo couple's analysis, made by the same core (draws the landing picture)
//   public/assets.json        what the worker loads (names, versions, hash)
//   public/licenses.txt       the licences of everything third-party that ships with the site
import { copyFileSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync, existsSync } from "node:fs";
import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const web = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const root = resolve(web, "..");
const pub = join(web, "public");

// 1. Pyodide core files
const pyoSrc = join(web, "node_modules", "pyodide");
const pyoDst = join(pub, "pyodide");
rmSync(pyoDst, { recursive: true, force: true });
mkdirSync(pyoDst, { recursive: true });
for (const f of ["pyodide.js", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"]) {
  copyFileSync(join(pyoSrc, f), join(pyoDst, f));
}
const pyoPkg = JSON.parse(readFileSync(join(pyoSrc, "package.json"), "utf8"));
const lock = JSON.parse(readFileSync(join(pyoSrc, "pyodide-lock.json"), "utf8"));

// 2. the core as a wheel (prefer the project venv, then the system python)
const wheelDir = join(pub, "wheels");
rmSync(wheelDir, { recursive: true, force: true });
mkdirSync(wheelDir, { recursive: true });
// a cached build/ directory can ship stale code, so always build from a clean slate
for (const d of ["build", "lovelm.egg-info"]) rmSync(join(root, "core", d), { recursive: true, force: true });
const pythons = [join(root, ".venv", "bin", "python"), "python3"].filter((p) => p === "python3" || existsSync(p));
let built = false;
for (const py of pythons) {
  for (const extra of [["--no-build-isolation"], []]) {
    const r = spawnSync(py, ["-m", "pip", "wheel", join(root, "core"), "--no-deps", "--quiet", "-w", wheelDir, ...extra], { encoding: "utf8" });
    if (r.status === 0 && readdirSync(wheelDir).some((f) => f.endsWith(".whl"))) { built = true; break; }
  }
  if (built) break;
}
if (!built) throw new Error("could not build the lovelm wheel (need pip + setuptools + wheel)");
const wheel = readdirSync(wheelDir).find((f) => f.endsWith(".whl"));
const sha = createHash("sha256").update(readFileSync(join(wheelDir, wheel))).digest("hex");

// 3. the demo chat
mkdirSync(join(pub, "demo"), { recursive: true });
copyFileSync(join(root, "demo", "demo_chat.txt"), join(pub, "demo", "demo_chat.txt"));
const analyzeDemo = [
  "import json, sys",
  `sys.path.insert(0, ${JSON.stringify(join(root, "core"))})`,
  "from lovelm.api import load_chat, analyze",
  `chat = load_chat(open(${JSON.stringify(join(root, "demo", "demo_chat.txt"))}, "rb").read())`,
  "print(json.dumps(analyze(chat, seed=1234, spicy=False, quotes=True), ensure_ascii=False, separators=(',', ':')))",
].join("\n");
const demoResult = pythons.map((py) => spawnSync(py, ["-c", analyzeDemo], { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 }))
  .find((r) => r.status === 0);
if (!demoResult) throw new Error("could not analyse the demo chat for the landing picture");
writeFileSync(join(pub, "demo", "demo-result.json"), demoResult.stdout);

// 4. third-party licences (linked from the footer). The OFL texts come straight from the font packages.
const text = (...p) => readFileSync(join(...p), "utf8").trim();
const rule = "=".repeat(78);
const fontSections = ["dm-serif-display", "inter"].map((name) => {
  const dir = join(web, "node_modules", "@fontsource", name);
  return `${rule}\nFont: @fontsource/${name} ${JSON.parse(text(dir, "package.json")).version} (SIL Open Font License 1.1)\n${rule}\n\n${text(dir, "LICENSE")}`;
});
writeFileSync(join(pub, "licenses.txt"), [
  "Love Language Model: licences of what ships with this site\n\nThe site is self-hosted: every file below is served from the same place as the page, never from a CDN.",
  `${rule}\nLove Language Model (this project) (MIT)\n${rule}\n\n${text(root, "LICENSE")}`,
  `${rule}\nPyodide ${pyoPkg.version} (Mozilla Public License 2.0)\n${rule}\n\nThe Python runtime in your browser (pyodide.js, pyodide.asm.js, pyodide.asm.wasm, python_stdlib.zip) is served unmodified from /pyodide/.\nSource code: https://github.com/pyodide/pyodide\nLicence text: https://www.mozilla.org/MPL/2.0/`,
  `${rule}\nCPython ${lock.info.python} (Python Software Foundation License 2.0)\n${rule}\n\nPyodide is CPython compiled to WebAssembly; the standard library is in python_stdlib.zip.\nSource code: https://github.com/python/cpython\nLicence text: https://docs.python.org/3/license.html`,
  ...fontSections,
].join("\n\n") + "\n");

writeFileSync(join(pub, "assets.json"), JSON.stringify({
  pyodide: pyoPkg.version, python: lock.info.python, wheel: `wheels/${wheel}`, wheelSha256: sha.slice(0, 16),
}, null, 2) + "\n");
console.log(`assets ready: pyodide ${pyoPkg.version} (python ${lock.info.python}), ${wheel} [${sha.slice(0, 8)}]`);
