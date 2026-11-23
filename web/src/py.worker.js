// The Python engine. A classic worker (so it can importScripts Pyodide) with no imports of its own:
// the main thread hands it the glue source. Chat bytes arrive as a transferred ArrayBuffer and never
// go anywhere else; this worker makes no network request after init.
let pyodide = null;
let fns = {};

const post = (m) => self.postMessage(m);

const handlers = {
  async init({ base, glue }) {
    const t0 = performance.now();
    post({ type: "progress", stage: "runtime" });
    importScripts(base + "pyodide/pyodide.js");
    pyodide = await self.loadPyodide({ indexURL: base + "pyodide/" });
    post({ type: "progress", stage: "engine" });
    const assets = await (await fetch(base + "assets.json")).json();
    const wheel = await (await fetch(base + assets.wheel + "?v=" + assets.wheelSha256)).arrayBuffer();
    pyodide.unpackArchive(wheel, "wheel"); // a pure-Python wheel: unzip into site-packages, no micropip
    pyodide.runPython(glue);
    fns = { load: pyodide.globals.get("load"), analyze: pyodide.globals.get("analyze"), burn: pyodide.globals.get("burn") };
    return {
      pyodide: pyodide.version,
      python: pyodide.runPython("import sys; sys.version.split()[0]"),
      wheel: assets.wheel,
      ms: Math.round(performance.now() - t0),
    };
  },
  async load({ bytes, dateOrder }) {
    return JSON.parse(fns.load(new Uint8Array(bytes), dateOrder ?? null));
  },
  async analyze(options) {
    return JSON.parse(fns.analyze(JSON.stringify(options)));
  },
  async burn() {
    return JSON.parse(fns.burn());
  },
  async resources() {
    // what this worker has fetched, for the "watch the network" panel
    return performance.getEntriesByType("resource").map((e) => e.name);
  },
};

self.onmessage = async ({ data: { id, type, payload } }) => {
  try {
    post({ id, ok: true, result: await handlers[type](payload) });
  } catch (err) {
    post({ id, ok: false, error: { message: String(err && err.message ? err.message : err) } });
  }
};
