// The "don't trust us, watch" panel. Browsers keep a timeline of every network request a page and a
// worker make. We note how long both timelines are at the moment the chat is in memory, and later list
// anything that was requested after that. For a real run the list is empty, and you can confirm it
// yourself in DevTools -> Network.
export function createPrivacy(engine) {
  let baseline = null;
  const mainRequests = () => performance.getEntriesByType("resource").map((e) => e.name);

  return {
    /** Call the moment the chat's bytes are in memory, before they go to the worker. */
    async mark() {
      baseline = { main: mainRequests().length, worker: (await engine.resources()).length };
    },
    /** URLs requested since mark() by the page or the Python worker (null if nothing was marked). */
    async since() {
      if (!baseline) return null;
      return [...mainRequests().slice(baseline.main), ...(await engine.resources()).slice(baseline.worker)];
    },
    /** Everything fetched before the chat appeared: the site itself, Pyodide and the wheel. */
    async before() {
      const names = [...mainRequests(), ...(await engine.resources())];
      return baseline ? names.slice(0, baseline.main + baseline.worker) : names;
    },
    reset() {
      baseline = null;
    },
  };
}

/** Short, readable name for a URL in a request list. */
export function shortName(url) {
  try {
    const u = new URL(url);
    return (u.origin === location.origin ? "" : u.origin) + u.pathname.replace(/^.*\/(?=[^/]+\/[^/]+$)/, "…/");
  } catch {
    return url;
  }
}

/** True when a URL is not on this site's own origin. */
export const isExternal = (url) => {
  try {
    return new URL(url).origin !== location.origin;
  } catch {
    return true;
  }
};
