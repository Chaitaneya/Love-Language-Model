import { readFileSync } from "node:fs";
import { crc32, deflateSync } from "node:zlib";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export const DEMO = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "demo", "demo_chat.txt");
export const demoBytes = () => readFileSync(DEMO);

/** A valid PNG (gradient plus two dark "heads") built from scratch, so the photo tests need no fixture files. */
export function makePng(w = 640, h = 480) {
  const raw = Buffer.alloc((w * 3 + 1) * h);
  for (let y = 0; y < h; y++) {
    const row = y * (w * 3 + 1);
    for (let x = 0; x < w; x++) {
      const head = (cx) => (x - cx) ** 2 + (y - h * 0.45) ** 2 < (h * 0.17) ** 2;
      const [r, g, b] = head(w * 0.38) || head(w * 0.6) ? [24, 22, 20] : [Math.round(60 + (x / w) * 180), Math.round(80 + (y / h) * 110), Math.round(200 - (y / h) * 150)];
      raw[row + 1 + x * 3] = r; raw[row + 2 + x * 3] = g; raw[row + 3 + x * 3] = b;
    }
  }
  const chunk = (type, data) => {
    const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
    const body = Buffer.concat([Buffer.from(type), data]);
    const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(body));
    return Buffer.concat([len, body, crc]);
  };
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4); ihdr[8] = 8; ihdr[9] = 2;
  return Buffer.concat([Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]), chunk("IHDR", ihdr), chunk("IDAT", deflateSync(raw)), chunk("IEND", Buffer.alloc(0))]);
}

export const pngSize = (buf) => ({ sig: [...buf.subarray(0, 8)], width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) });

/** Wait until Python AND the fonts are ready: after this, nothing legitimate is left to download. */
export async function ready(page) {
  await page.waitForFunction(() => document.documentElement.dataset.engine === "ready");
  await page.evaluate(async () => { await document.fonts.ready; });
}

/** A cheap fingerprint of what the poster canvas currently shows. */
export const canvasFingerprint = (page) => page.evaluate(async () => {
  // the poster redraws on the next animation frame after any edit, so let two frames pass first
  await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  const c = document.querySelector("#poster-canvas"), d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
  let h = 0, colours = new Set();
  for (let i = 0; i < d.length; i += 4 * 211) { h = (h * 31 + d[i] + d[i + 1] * 3 + d[i + 2] * 7) >>> 0; colours.add((d[i] >> 4) * 256 + (d[i + 1] >> 4) * 16 + (d[i + 2] >> 4)); }
  return { hash: h, colours: colours.size };
});

/**
 * Keep a copy of the poster's pixels in the page under `key`, to compare later with `snapshotDiff`.
 * Exact equality is the wrong test: after the canvas has been read back twice, Chrome moves it from GPU
 * to software rasterisation, and the next draw then differs by a level or two in most pixels (grain and
 * gradient rounding; measured: 98% of changed pixels move by 1-3 levels, mean change 0.06). That is not
 * something anyone can see, so the comparison below measures what is visible.
 */
export const snapshot = (page, key) => page.evaluate(async (key) => {
  await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  const c = document.querySelector("#poster-canvas");
  (window.__snaps ??= {})[key] = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
}, key);

/** meanDelta: average per-channel change; visible: how many pixels changed by more than 8 levels. */
export const snapshotDiff = (page, a, b) => page.evaluate(([a, b]) => {
  const A = window.__snaps[a], B = window.__snaps[b];
  let total = 0, visible = 0;
  for (let i = 0; i < A.length; i += 4) {
    const dr = Math.abs(A[i] - B[i]), dg = Math.abs(A[i + 1] - B[i + 1]), db = Math.abs(A[i + 2] - B[i + 2]);
    total += dr + dg + db;
    if (Math.max(dr, dg, db) > 8) visible++;
  }
  const pixels = A.length / 4;
  return { pixels, visible, visibleShare: visible / pixels, meanDelta: total / (pixels * 3) };
}, [a, b]);
