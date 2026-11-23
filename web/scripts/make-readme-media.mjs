// Makes the pictures the README shows, from the real production build, driven in your installed Chrome:
//   docs/img/poster.jpg   the demo couple's poster (exactly what "Download PNG" produces, shrunk for the page)
//   docs/img/demo.gif     a phone-sized tour: landing, names, the six highlights, the four cards, the receipts
// Needs: a production build (npm run build), Google Chrome, ffmpeg, and macOS `sips` (or Pillow) for the JPEG.
//   usage: npm run media            (use --keep-frames to leave the PNG frames in a temp folder)
import { spawn, spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync, existsSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";

const web = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const out = resolve(web, "..", "docs", "img");
const PORT = 4173, BASE = `http://localhost:${PORT}/`;
const keep = process.argv.includes("--keep-frames");
if (!existsSync(join(web, "dist", "index.html"))) throw new Error("no production build: run `npm run build` first");
mkdirSync(out, { recursive: true });
const frames = mkdtempSync(join(tmpdir(), "llm-frames-"));

// serve the production build (same CSP as the real site)
const server = spawn("npx", ["vite", "preview", "--port", String(PORT), "--strictPort"], { cwd: web, stdio: "ignore" });
const up = async () => { for (let i = 0; i < 60; i++) { try { if ((await fetch(BASE)).ok) return; } catch {} await new Promise((r) => setTimeout(r, 500)); } throw new Error("preview server did not start"); };

const scenes = []; // { file, seconds }
try {
  await up();
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const page = await (await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, acceptDownloads: true })).newPage();
  await page.goto(BASE);
  await page.waitForFunction(() => document.documentElement.dataset.engine === "ready");
  await page.evaluate(async () => { await document.fonts.ready; });

  let n = 0;
  const shot = async (seconds) => {
    const file = join(frames, `f${String(++n).padStart(2, "0")}.png`);
    await page.screenshot({ path: file });
    scenes.push({ file, seconds });
  };
  const settle = (ms = 700) => page.waitForTimeout(ms);

  await settle(1200);
  await shot(2.4);                                                   // 1. landing, with the demo poster
  await page.click("#go-demo");
  await page.locator("#names").waitFor({ state: "visible", timeout: 60_000 });
  await settle();
  await shot(1.6);                                                   // 2. names
  await page.click("#names-done");
  for (let i = 0; i < 6; i++) {                                      // 3-8. the six highlights
    await settle(900);
    await shot(i === 0 ? 2.2 : 2.6);
    await page.click("#next");
  }
  await page.locator("#poster").waitFor({ state: "visible" });
  await settle(900);
  await shot(3.2);                                                   // 9. the poster
  for (const tab of ["Words", "Cast", "Hour"]) {                     // 10-12. the other cards
    await page.getByRole("tab", { name: tab }).click();
    await settle(1100);
    await shot(2.2);
  }
  await page.getByRole("tab", { name: "Poster" }).click();
  await settle(900);

  // the poster image for the README: the real export, shrunk
  const [download] = await Promise.all([page.waitForEvent("download"), page.click("#save-btn")]);
  const pngPath = join(frames, "poster.png");
  await download.saveAs(pngPath);
  const jpg = join(out, "poster.jpg");
  const sips = spawnSync("sips", ["-s", "format", "jpeg", "-s", "formatOptions", "84", "-Z", "960", pngPath, "--out", jpg], { encoding: "utf8" });
  if (sips.status !== 0) {
    const py = spawnSync("python3", ["-c", "import sys;from PIL import Image;im=Image.open(sys.argv[1]).convert('RGB');im.thumbnail((960,960));im.save(sys.argv[2],quality=84,optimize=True)", pngPath, jpg], { encoding: "utf8" });
    if (py.status !== 0) throw new Error(`could not write poster.jpg: ${sips.stderr || py.stderr}`);
  }

  await page.click("#open-receipts");
  await settle(1200);
  await shot(2.8);                                                   // 9. how we counted
  await browser.close();

  // frames -> gif (one shared palette keeps the file small and the poster's gold gold)
  const list = join(frames, "list.txt");
  writeFileSync(list, scenes.map((s) => `file '${s.file}'\nduration ${s.seconds}`).join("\n") + `\nfile '${scenes.at(-1).file}'\n`);
  const gif = join(out, "demo.gif");
  const ff = spawnSync("ffmpeg", ["-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", list,
    "-vf", "fps=10,scale=390:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=5", "-loop", "0", gif], { encoding: "utf8" });
  if (ff.status !== 0) throw new Error(`ffmpeg failed: ${ff.stderr}`);
  const kb = (f) => (statSync(f).size / 1024).toFixed(0);
  console.log(`wrote ${jpg} (${kb(jpg)} KB) and ${gif} (${kb(gif)} KB)`);
  if (keep) console.log(`frames kept in ${frames}`);
} finally {
  server.kill();
  if (!keep) rmSync(frames, { recursive: true, force: true });
}
