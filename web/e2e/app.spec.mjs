import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test, expect } from "./fixtures.mjs";
import { DEMO, canvasFingerprint, makePng, pngSize, ready, snapshot, snapshotDiff } from "./helpers.mjs";

const asFile = (name, text) => ({ name, mimeType: "text/plain", buffer: Buffer.from(text) });
const chatLines = (n, who) => Array.from({ length: n }, (_, i) => `13/01/24, 10:${String(i % 60).padStart(2, "0")} am - ${who[i % who.length]}: hi`).join("\n");
const noSidewaysScroll = (page) => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth);
const slide = (page) => page.locator("#track .slide[aria-hidden=false]");

async function addChat(page, file) {
  if (!(await page.locator("#add").isVisible())) await page.click("#go-add");
  await page.setInputFiles("#chat-file", file);
}
async function throughToPoster(page) {
  await page.click("#names-done");
  await expect(page.locator("#reveal")).toBeVisible();
  for (let i = 0; i < 4; i++) await page.click("#next");
  await expect(page.locator("#next")).toHaveText("Make our poster");
  await page.click("#next");
  await expect(page.locator("#poster")).toBeVisible();
}

test("the demo couple, start to poster, and nothing is requested after the chat is fetched", async ({ page, net }) => {
  await page.goto("/");
  await expect(page.locator("#preview-caption")).toHaveText("Rohan & Tara, a demo couple"); // the landing picture
  await ready(page);
  await page.click("#go-demo");
  await expect(page.locator("#names")).toBeVisible({ timeout: 60_000 });
  await expect(page.locator("#name-a-label")).toHaveText("Sent 28,429 messages");
  await throughToPoster(page);
  await expect(page.locator("#poster-canvas")).toHaveAttribute("aria-label", /Poster titled hmm\. Rohan sent 31 messages in a row\. Tara said ‘I love you’ first\./);
  expect((await canvasFingerprint(page)).colours, "the poster is not blank").toBeGreaterThan(6);

  const demoIndex = net.log.findIndex((r) => r.url.endsWith("/demo/demo_chat.txt"));
  expect(demoIndex).toBeGreaterThan(-1);
  expect(net.log.slice(demoIndex + 1), "after the demo chat is fetched, no further request at all").toEqual([]);
  await page.click("#open-how");
  await expect(page.locator("#net-count")).toHaveText("0");
});

test("your own chat: zero network requests from 'ready' to the poster and the receipts", async ({ page, net }) => {
  await page.goto("/");
  await ready(page);
  net.mark(); // from here on, the chat is about to enter the page. Nothing may be requested.

  await addChat(page, DEMO);
  await expect(page.locator("#names")).toBeVisible({ timeout: 60_000 });
  await page.fill("#name-a", "Chai");
  await page.fill("#name-b", "Chitra");
  await page.click("#names-done");

  const texts = [];
  for (let i = 0; i < 5; i++) {
    texts.push(await slide(page).innerText());
    await page.click("#next");
  }
  const all = texts.join("\n");
  expect(all).toContain("“hi, is this Tara?”"); // a real quote is never rewritten
  expect(all).toContain("Chai");
  expect(all).toMatch(/Chitra said “I\s+love\s+you” first\./); // the words are held together with no-break spaces
  expect(all).toContain("Slower to reply, first to say it.");
  expect(all, "no scores, weights or decimals on the main path").not.toMatch(/\d\.\d|score|weight/i);
  await expect(page.locator("#poster")).toBeVisible();
  await expect(page.locator("#poster-canvas")).toHaveAttribute("aria-label", /Chai sent 31 messages in a row/);

  await page.click("#open-receipts");
  await expect(page.locator("#sheet-title")).toHaveText("How we counted");
  await expect(page.locator("#sheet-body")).toContainText("What counting can’t tell you");
  await expect(page.locator("#sheet-body")).not.toContainText(/\d\.\d|\d+%\s*weight|score:/i); // no decimals, no weighted scores
  await page.keyboard.press("Escape");
  await expect(page.locator("#sheet")).toBeHidden();

  expect(net.since(), "no request after the chat entered the page").toEqual([]);
  await page.click("#open-how");
  await expect(page.locator("#net-count")).toHaveText("0");
});

test("the highlights move by tap, swipe and keys; Skip and browser Back work", async ({ page }) => {
  await page.goto("/");
  await ready(page);
  await page.click("#go-demo");
  await page.click("#names-done");
  await expect(slide(page)).toContainText("hi, is this Tara?");

  const box = await page.locator("#stage").boundingBox();
  await page.mouse.click(box.x + box.width * 0.8, box.y + box.height / 2); // tap the right side: forward
  await expect(slide(page)).toContainText("How long a reply usually takes");
  await page.mouse.click(box.x + box.width * 0.1, box.y + box.height / 2); // tap the left third: back
  await expect(slide(page)).toContainText("hi, is this Tara?");

  const y = box.y + box.height / 2; // a swipe to the left, with some speed
  await page.mouse.move(box.x + box.width * 0.8, y);
  await page.mouse.down();
  for (let i = 1; i <= 8; i++) await page.mouse.move(box.x + box.width * (0.8 - i * 0.07), y);
  await page.mouse.up();
  await expect(slide(page)).toContainText("How long a reply usually takes");
  await page.keyboard.press("ArrowRight");
  await expect(slide(page)).toContainText("31 messages in a row");

  await page.click("#skip");
  await expect(page.locator("#poster")).toBeVisible();
  await page.goBack();
  await expect(page.locator("#reveal")).toBeVisible();
  await page.goBack();
  await expect(page.locator("#names")).toBeVisible();
});

test("a photo, then a real PNG: 1080 x 1920, no names in the filename, no network", async ({ page, net }) => {
  await page.goto("/");
  await ready(page);
  await page.click("#go-demo");
  await page.click("#names-done");
  await page.click("#skip");
  net.mark();

  await snapshot(page, "plain");
  const plain = await canvasFingerprint(page);
  await page.setInputFiles("#photo-file", { name: "us.png", mimeType: "image/png", buffer: makePng() });
  await expect(page.locator("#photo-btn")).toHaveText("Remove photo");
  const withPhoto = await canvasFingerprint(page);
  expect(withPhoto.hash).not.toBe(plain.hash);
  await snapshot(page, "withPhoto");

  const [download] = await Promise.all([page.waitForEvent("download"), page.click("#save-btn")]);
  expect(download.suggestedFilename()).toBe("love-language-model-poster.png");
  const path = join(mkdtempSync(join(tmpdir(), "llm-")), "poster.png");
  await download.saveAs(path);
  const png = readFileSync(path), info = pngSize(png);
  expect(info.sig).toEqual([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
  expect([info.width, info.height]).toEqual([1080, 1920]);
  expect(png.length).toBeLessThan(8 * 1024 * 1024);

  await page.click("#photo-btn"); // remove it
  await expect(page.locator("#photo-btn")).toHaveText("Add a photo");
  await snapshot(page, "removed");
  const back = await snapshotDiff(page, "plain", "removed");
  // removing the photo gives the plain poster back (not bit-for-bit after a read-back: see helpers.mjs)
  expect(back.meanDelta, "no visible change on average").toBeLessThan(1);
  expect(back.visibleShare, "under 1% of pixels changed by more than 8 levels").toBeLessThan(0.01);
  expect((await snapshotDiff(page, "plain", "withPhoto")).meanDelta, "and this check does notice a real change").toBeGreaterThan(3);

  await page.click("[data-title-index='1'], .seg-btn >> nth=1"); // the other title
  await expect(page.locator("#poster-canvas")).toHaveAttribute("aria-label", /Poster titled Rohan & Tara/);
  expect(net.since()).toEqual([]);
});

test("files that are not a usable chat get a straight answer", async ({ page }) => {
  await page.goto("/");
  await ready(page);
  const title = page.locator("#dialog-title");
  const again = () => page.getByRole("button", { name: "Choose another file" }).click();

  await addChat(page, asFile("garbage.txt", "hello\nthis is not a chat\n"));
  await expect(title).toHaveText("We couldn't read that file.");
  await again();
  await expect(page.locator("#add-choose")).toBeVisible();

  await addChat(page, asFile("trailer.txt", chatLines(10, ["Ann", "Bo"])));
  await expect(title).toHaveText("This isn't a movie, it's a trailer.");
  await again();

  await addChat(page, asFile("cast.txt", chatLines(400, ["A", "B", "C", "D", "E", "F"])));
  await expect(title).toHaveText("6 people? That's not a couple, that's a cast.");
  await again();

  await addChat(page, asFile("dates.txt", "03/04/24, 10:00 am - Ann: hi\n05/04/24, 10:00 am - Bo: yo\n07/04/24, 10:00 am - Ann: hey\n"));
  await expect(title).toHaveText("One question about the dates");
  await page.getByRole("button", { name: "March 4th" }).click();
  await expect(title).toHaveText("This isn't a movie, it's a trailer."); // it asked, we answered, then it counted
});

test("going Back while a chat is being read cancels it; it never jumps ahead later", async ({ page }) => {
  await page.goto("/");
  await ready(page);
  await addChat(page, DEMO);
  await expect(page.locator("#add-loading")).toBeVisible();
  await page.goBack();
  await expect(page.locator("#landing")).toBeVisible();
  await page.waitForTimeout(6000); // longer than reading and counting the demo takes
  await expect(page.locator("#landing")).toBeVisible();
  await expect(page.locator("#names")).toBeHidden();
});

test("on a phone: no sideways scrolling on any screen, and the poster fits", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/");
  await ready(page);
  expect(await noSidewaysScroll(page), "landing").toBe(true);
  await page.click("#go-add");
  expect(await noSidewaysScroll(page), "add").toBe(true);
  await page.click("#add-demo");
  await expect(page.locator("#names")).toBeVisible({ timeout: 60_000 });
  expect(await noSidewaysScroll(page), "names").toBe(true);
  await page.click("#names-done");
  for (let i = 0; i < 5; i++) {
    expect(await noSidewaysScroll(page), `highlight ${i + 1}`).toBe(true);
    await page.click("#next");
  }
  const w = await page.locator("#poster-canvas").evaluate((c) => c.getBoundingClientRect().width);
  expect(w).toBeLessThanOrEqual(375);
  expect(await noSidewaysScroll(page), "poster").toBe(true);
  await page.click("#open-receipts");
  expect(await noSidewaysScroll(page), "receipts").toBe(true);
});

test("Start over forgets the chat and comes back to the landing page", async ({ page }) => {
  await page.goto("/");
  await ready(page);
  await page.click("#go-demo");
  await page.click("#names-done");
  await page.click("#skip");
  await page.click("#restart");
  await expect(page.locator("#landing")).toBeVisible();
  await ready(page);
  await page.click("#open-how");
  await expect(page.locator("#net-count")).toHaveText("—"); // no chat in memory any more
});

test("the licences are one click away, and the 404 page is styled under its own CSP", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Licences" }).click();
  await expect(page).toHaveURL(/licenses\.txt$/);
  const text = await page.locator("body").innerText();
  for (const needle of ["Pyodide", "CPython", "dm-serif-display", "Inter Project Authors", "SIL Open Font License"]) expect(text).toContain(needle);

  await page.goto("/404.html");
  await expect(page.getByRole("heading", { name: "Left on read." })).toBeVisible();
  // the inline <style> is allowed only by hash: if the hash were wrong, Chrome would block it and report a CSP error
  const h1 = await page.locator("h1").evaluate((el) => getComputedStyle(el).textTransform);
  expect(h1, "the page's own CSS applied").toBe("uppercase");
});
