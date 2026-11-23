// The 404 page has to work from any URL depth on a static host, so it carries its one <style> inline
// and its own CSP allows exactly that style by hash. Edit the CSS and forget the hash, and the page
// loads unstyled: this test catches that.
import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../public/404.html", import.meta.url), "utf8");

test("404.html: its CSP allows its inline <style> by hash, and nothing else is inline", () => {
  const styles = [...html.matchAll(/<style>([\s\S]*?)<\/style>/g)];
  assert.equal(styles.length, 1, "exactly one style block");
  const hash = createHash("sha256").update(styles[0][1]).digest("base64");
  const csp = html.match(/http-equiv="Content-Security-Policy" content="([^"]+)"/)?.[1] ?? "";
  assert.ok(csp.includes(`style-src 'sha256-${hash}'`), "style hash in the CSP matches the style block");
  assert.ok(!/<script/i.test(html), "no scripts");
  assert.ok(!/\sstyle=/i.test(html.replace(/<style>[\s\S]*?<\/style>/g, "")), "no style attributes");
  assert.match(csp, /default-src 'none'/);
});

test("404.html: says what it should, and links back to the site root", () => {
  assert.match(html, /Left on read\./);
  assert.match(html, /<a href="\/">/);
});
