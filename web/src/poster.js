// Draws the 1080 x 1920 poster. The same canvas is shown on screen and saved as the PNG.
//
// One idea: a column of messages on one side, a single short reply on the other, and the reply as the
// title. Every bar is one real message from the longest run, as long as that message was (the core
// sends the lengths), so the picture is the data, not decoration. With a photo, the photo becomes the
// image and the type stays.

export const W = 1080;
export const H = 1920;
const M = 96; // outer margin

const PAPER = "#ECE4D6";
const INK = "#1B1715";
const RED = "#B8322A";
const RED_ON_DARK = "#F0634C";
const CREAM = "#F4EDE3";

// Small deterministic random numbers, so the film grain is identical on every export.
function rng(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

// Tracked text. Native letterSpacing keeps the font's kerning; where a browser lacks it, glyphs are
// placed one by one.
function tracked(ctx, text, x, y, tracking, align = "left") {
  if ("letterSpacing" in ctx) {
    ctx.letterSpacing = `${tracking}px`;
    ctx.textAlign = align;
    ctx.fillText(text, align === "right" ? x + tracking : x, y); // letterSpacing pads after the last glyph
    ctx.letterSpacing = "0px";
    ctx.textAlign = "left";
    return;
  }
  const chars = [...text];
  const widths = chars.map((ch) => ctx.measureText(ch).width);
  const total = widths.reduce((a, b) => a + b, 0) + tracking * (chars.length - 1);
  let cx = align === "right" ? x - total : align === "center" ? x - total / 2 : x;
  ctx.textAlign = "left";
  chars.forEach((ch, i) => {
    ctx.fillText(ch, cx, y);
    cx += widths[i] + tracking;
  });
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

let grainTile = null;
function grain(ctx, alpha) {
  if (!grainTile) {
    grainTile = document.createElement("canvas");
    grainTile.width = grainTile.height = 192;
    const g = grainTile.getContext("2d");
    const img = g.createImageData(192, 192);
    const rand = rng(7);
    for (let i = 0; i < img.data.length; i += 4) {
      const v = rand() * 255;
      img.data[i] = img.data[i + 1] = img.data[i + 2] = v;
      img.data[i + 3] = 255;
    }
    g.putImageData(img, 0, 0);
  }
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.globalCompositeOperation = "overlay";
  ctx.fillStyle = ctx.createPattern(grainTile, "repeat");
  ctx.fillRect(0, 0, W, H);
  ctx.restore();
}

// Fit a title into the measure: shrink first, then split "A & B" over two lines.
function titleLayout(ctx, text, maxSize, measure) {
  ctx.font = `400 ${maxSize}px "DM Serif Display"`;
  const w = ctx.measureText(text).width;
  if (w <= measure) return { size: maxSize, lines: [text] };
  const amp = text.indexOf(" & ");
  if (amp > 0) {
    const lines = [text.slice(0, amp), text.slice(amp + 1)];
    const widest = Math.max(...lines.map((l) => ctx.measureText(l).width));
    return { size: Math.min(maxSize, Math.floor((maxSize * measure) / widest)), lines };
  }
  return { size: Math.floor((maxSize * measure) / w), lines: [text] };
}

/**
 * Bar geometry for a run of messages: one bar per message, width from its real length. Pure, so it is
 * unit-tested. Long runs get thinner bars (a 108-message run still fits the same column).
 */
export function barLayout(lens, n, { top = 256, bottom = 1046, maxW = 560, minW = 36 } = {}) {
  const count = Math.max(1, n);
  const span = bottom - top;
  const barH = Math.max(1, Math.min(18, span / (count * 1.45))); // 400 bars (the most the core sends) still fit
  const gap = count > 1 ? (span - count * barH) / (count - 1) : 0;
  const real = lens.length === count ? lens : Array.from({ length: count }, (_, i) => lens[i] ?? 0);
  const longest = Math.max(1, ...real);
  return {
    barH,
    gap,
    bars: real.map((len, i) => ({
      y: top + i * (barH + gap),
      // square root keeps one very long message from flattening the rest; a photo (0) is a short stub
      w: Math.round(minW + (maxW - minW) * Math.sqrt(len / longest)),
    })),
  };
}

// Draw the photo cover-cropped and graded warm, so any phone photo sits in the palette.
export function preparePhoto(bitmap) {
  const c = document.createElement("canvas");
  c.width = W;
  c.height = H;
  const g = c.getContext("2d", { willReadFrequently: true });
  const scale = Math.max(W / bitmap.width, H / bitmap.height);
  const dw = bitmap.width * scale;
  const dh = bitmap.height * scale;
  g.drawImage(bitmap, (W - dw) / 2, (H - dh) * 0.4, dw, dh); // faces sit high in most photos
  const img = g.getImageData(0, 0, W, H);
  const d = img.data;
  for (let i = 0; i < d.length; i += 4) {
    const r = d[i], gr = d[i + 1], b = d[i + 2];
    const l = 0.2126 * r + 0.7152 * gr + 0.0722 * b;
    // 28% toward grey, a gentle S-curve, then a warm cast.
    d[i] = curve(r + (l - r) * 0.28) + 10;
    d[i + 1] = curve(gr + (l - gr) * 0.28) + 2;
    d[i + 2] = curve(b + (l - b) * 0.28) - 8;
  }
  g.putImageData(img, 0, 0);
  return c;
}
function curve(v) {
  const x = v / 255;
  const y = x < 0.5 ? 2 * x * x : 1 - 2 * (1 - x) * (1 - x);
  return (x * 0.6 + y * 0.4) * 235;
}

export function drawPoster(canvas, content, { title = 0, photo = null } = {}) {
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d");
  const dark = Boolean(photo);
  const ink = dark ? CREAM : INK;
  const chosen = content.titles[Math.min(title, content.titles.length - 1)];
  const isWord = chosen.key === "word";

  // Ground
  if (dark) {
    ctx.drawImage(photo, 0, 0);
    let g = ctx.createLinearGradient(0, 0, 0, 420);
    g.addColorStop(0, "rgba(16,12,10,0.55)");
    g.addColorStop(1, "rgba(16,12,10,0)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W, 420);
    g = ctx.createLinearGradient(0, H * 0.45, 0, H);
    g.addColorStop(0, "rgba(16,12,10,0)");
    g.addColorStop(0.45, "rgba(16,12,10,0.72)");
    g.addColorStop(1, "rgba(16,12,10,0.94)");
    ctx.fillStyle = g;
    ctx.fillRect(0, H * 0.45, W, H * 0.55);
  } else {
    ctx.fillStyle = PAPER;
    ctx.fillRect(0, 0, W, H);
  }

  // Billing: the two names, each on the side their messages sit.
  ctx.fillStyle = ink;
  ctx.font = '600 26px "Inter"';
  ctx.textBaseline = "alphabetic";
  ctx.globalAlpha = 0.9;
  tracked(ctx, content.left.toUpperCase(), M, 168, 26 * 0.22);
  tracked(ctx, content.right.toUpperCase(), W - M, 168, 26 * 0.22, "right");
  ctx.globalAlpha = 1;

  // The image: the run of messages on the right, the one short reply on the left.
  if (!dark && content.monologue) {
    const { barH, gap, bars } = barLayout(content.monologue.lens, content.monologue.n);
    ctx.fillStyle = INK;
    for (const b of bars) {
      roundRect(ctx, W - M - b.w, b.y, b.w, barH, barH / 2);
      ctx.fill();
    }
    const replyH = Math.max(barH, 8);
    ctx.fillStyle = RED;
    roundRect(ctx, M, 1046 + Math.max(gap, 12) * 2.2, 92, replyH, replyH / 2);
    ctx.fill();
  }

  // Title
  const measure = W - 2 * M;
  const t = titleLayout(ctx, chosen.text, isWord ? 330 : 190, measure);
  ctx.font = `400 ${t.size}px "DM Serif Display"`;
  ctx.fillStyle = isWord ? (dark ? RED_ON_DARK : RED) : ink;
  const lead = t.size * 0.92; // tight leading for display type
  const titleBase = 1494 - (t.lines.length - 1) * lead;
  t.lines.forEach((line, i) => tracked(ctx, line, M - t.size * 0.02, titleBase + i * lead, -t.size * 0.02)); // -2% tracking at display size

  // Tagline: two sentences that pull against each other.
  ctx.fillStyle = ink;
  ctx.font = 'italic 400 46px "DM Serif Display"';
  content.lines.forEach((line, i) => tracked(ctx, line, M, 1604 + i * 60, -0.2));

  // Credits
  ctx.font = '600 22px "Inter"';
  ctx.globalAlpha = dark ? 0.78 : 0.72;
  content.credits.forEach((line, i) => tracked(ctx, line, M, 1782 + i * 38, 22 * 0.16));
  tracked(ctx, "LOVE LANGUAGE MODEL", W - M, 1820, 22 * 0.16, "right");
  ctx.globalAlpha = 1;

  grain(ctx, dark ? 0.06 : 0.09);
}

// ---------------------------------------------------------------- the two other cards
// Same paper, margins, grain, title line and credits as the poster, so the three read as one set.

const TITLE_BASE = 1494;
const TAGLINE_TOP = 1604;

function paperGround(ctx) {
  ctx.fillStyle = PAPER;
  ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = INK;
  ctx.textBaseline = "alphabetic";
}

function caps(ctx, text, x, y, align = "left", size = 26, alpha = 0.9) {
  ctx.font = `600 ${size}px "Inter"`;
  ctx.globalAlpha = alpha;
  tracked(ctx, text.toUpperCase(), x, y, size * (size > 24 ? 0.22 : 0.16), align);
  ctx.globalAlpha = 1;
}

// Serif text that never runs past `max`: shrink it until it fits.
function fitSerif(ctx, text, size, max, style = "") {
  ctx.font = `${style} 400 ${size}px "DM Serif Display"`.trim();
  const w = ctx.measureText(text).width;
  if (w <= max) return size;
  const s = Math.floor((size * max) / w);
  ctx.font = `${style} 400 ${s}px "DM Serif Display"`.trim();
  return s;
}

function titleBlock(ctx, text, { color = INK, maxSize = 190, kicker = null } = {}) {
  const measure = W - 2 * M;
  const t = titleLayout(ctx, text, maxSize, measure);
  const lead = t.size * 0.92;
  const base = TITLE_BASE - (t.lines.length - 1) * lead;
  if (kicker) {
    ctx.fillStyle = INK;
    caps(ctx, kicker, M, base - t.size * 0.86 - 28, "left", 24, 0.72);
  }
  ctx.font = `400 ${t.size}px "DM Serif Display"`;
  ctx.fillStyle = color;
  t.lines.forEach((line, i) => tracked(ctx, line, M - t.size * 0.02, base + i * lead, -t.size * 0.02));
}

function taglines(ctx, lines) {
  ctx.fillStyle = INK;
  lines.forEach((line, i) => {
    fitSerif(ctx, line, 46, W - 2 * M, "italic");
    tracked(ctx, line, M, TAGLINE_TOP + i * 60, -0.2);
  });
}

// Bottom-anchored, so two or three lines both end where the poster's do.
function creditsBlock(ctx, lines) {
  ctx.fillStyle = INK;
  ctx.font = '600 22px "Inter"';
  ctx.globalAlpha = 0.72;
  lines.forEach((line, i) => tracked(ctx, line, M, 1820 - (lines.length - 1 - i) * 38, 22 * 0.16));
  tracked(ctx, "LOVE LANGUAGE MODEL", W - M, 1820, 22 * 0.16, "right");
  ctx.globalAlpha = 1;
}

/** Who says what: each person's words on their own side, alternating down the page like a chat. */
export function drawWordsCard(canvas, content) {
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d");
  paperGround(ctx);
  caps(ctx, content.left, M, 168);
  caps(ctx, content.right, W - M, 168, "right");

  const rows = [];
  const most = Math.max(content.cols[0].length, content.cols[1].length);
  for (let i = 0; i < most; i++) {
    if (content.cols[0][i]) rows.push({ ...content.cols[0][i], right: false });
    if (content.cols[1][i]) rows.push({ ...content.cols[1][i], right: true });
  }
  const top = 372;
  const step = rows.length > 1 ? Math.min(158, (1160 - top) / (rows.length - 1)) : 0;
  rows.forEach((r, i) => {
    const y = top + i * step;
    const x = r.right ? W - M : M;
    const size = fitSerif(ctx, r.w, 128, (W - 2 * M) * 0.72);
    ctx.fillStyle = r.accent ? RED : INK;
    tracked(ctx, r.w, r.right ? x + size * 0.02 : x - size * 0.02, y, -size * 0.02, r.right ? "right" : "left");
    ctx.fillStyle = INK;
    caps(ctx, r.note, x, y + 50, r.right ? "right" : "left", 20, 0.6);
  });

  titleBlock(ctx, content.title);
  taglines(ctx, content.lines);
  creditsBlock(ctx, content.credits);
  grain(ctx, 0.09);
}

/** The cast: a billing block. Each role is one counted behaviour, with both numbers. */
export function drawCastCard(canvas, content) {
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d");
  paperGround(ctx);
  caps(ctx, "The cast", M, 168);

  let y = 290;
  for (const person of content.people) {
    fitSerif(ctx, person.name, 112, W - 2 * M);
    ctx.fillStyle = INK;
    tracked(ctx, person.name, M - 2, y, -2);
    let r = y + 34;
    for (const role of person.roles) {
      ctx.globalAlpha = 0.16;
      ctx.fillRect(M, r, W - 2 * M, 2);
      ctx.globalAlpha = 1;
      ctx.font = '400 58px "DM Serif Display"';
      const valueW = ctx.measureText(role.value).width;
      tracked(ctx, role.value, W - M, r + 68, -0.6, "right");
      fitSerif(ctx, role.role, 50, W - 2 * M - valueW - 40, "italic");
      tracked(ctx, role.role, M, r + 66, -0.2);
      caps(ctx, role.note, W - M, r + 100, "right", 20, 0.6);
      r += 122;
    }
    y = r + 120;
  }

  if (content.pet) {
    titleBlock(ctx, `“${content.pet.token}”`, { color: RED, maxSize: 200, kicker: "And introducing" });
    taglines(ctx, [content.pet.line]);
  } else {
    titleBlock(ctx, content.names ?? "");
  }
  creditsBlock(ctx, content.credits);
  grain(ctx, 0.09);
}

/** The busiest hour: the 24 hours of your day as bars, from every message's timestamp, the peak in red. */
export function drawHourCard(canvas, content) {
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d");
  paperGround(ctx);
  caps(ctx, content.left, M, 168);
  caps(ctx, content.right, W - M, 168, "right");

  const top = 300, bottom = 1046, width = W - 2 * M;
  const gap = 10, barW = (width - gap * 23) / 24;
  const most = Math.max(1, ...content.totals);
  content.totals.forEach((n, h) => {
    const bh = n ? Math.max(6, (bottom - top) * (n / most)) : 3; // an empty hour is a hairline, not a gap
    ctx.fillStyle = h === content.peak ? RED : INK;
    roundRect(ctx, M + h * (barW + gap), bottom - bh, barW, bh, Math.min(barW / 2, 6));
    ctx.fill();
  });
  ctx.fillStyle = INK;
  for (const [h, label] of [[0, "12 AM"], [6, "6 AM"], [12, "12 PM"], [18, "6 PM"]]) {
    caps(ctx, label, M + h * (barW + gap), bottom + 46, "left", 20, 0.6);
  }

  titleBlock(ctx, content.title, { color: RED, maxSize: 330, kicker: content.kicker });
  taglines(ctx, content.lines);
  creditsBlock(ctx, content.credits);
  grain(ctx, 0.09);
}

