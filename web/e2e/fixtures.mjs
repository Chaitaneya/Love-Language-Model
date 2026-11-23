import { test as base, expect } from "@playwright/test";

/**
 * `net` records EVERY request the page, its workers and anything else in the browser context make.
 * At the end of each test it also asserts the standing rules: nothing leaves this site, and nothing
 * but plain GETs for our own static files happens.
 */
export const test = base.extend({
  net: async ({ context, baseURL, page }, use) => {
    const log = [], errors = [];
    context.on("request", (r) => log.push({ url: r.url(), method: r.method(), body: r.postData() }));
    page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
    page.on("pageerror", (e) => errors.push(String(e)));
    let marker = null;
    const net = {
      log, errors,
      mark: () => (marker = log.length),
      since: () => (marker == null ? [] : log.slice(marker).map((r) => r.url)),
    };
    await use(net);
    const origin = new URL(baseURL).origin;
    expect(log.filter((r) => new URL(r.url).origin !== origin && !r.url.startsWith("data:") && !r.url.startsWith("blob:")), "no request may leave this site").toEqual([]);
    expect(log.filter((r) => r.method !== "GET").map((r) => `${r.method} ${r.url}`), "nothing is ever sent (no POST/PUT)").toEqual([]);
    expect(log.filter((r) => r.body), "no request has a body").toEqual([]);
    expect(errors, "no console errors (this includes CSP violations)").toEqual([]);
  },
});
export { expect };
