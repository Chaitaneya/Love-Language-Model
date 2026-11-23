// Promise wrapper around the Python worker. One worker, one chat in its memory.
import glue from "./glue.py?raw";

export function createEngine({ onProgress = () => {} } = {}) {
  const base = new URL("./", document.baseURI).href;
  let worker = null;
  let nextId = 1;
  const pending = new Map();
  let ready = null;
  let info = null;

  function start() {
    worker = new Worker(new URL("./py.worker.js", import.meta.url));
    worker.onmessage = ({ data }) => {
      if (data.type === "progress") return onProgress(data.stage);
      const p = pending.get(data.id);
      if (!p) return;
      pending.delete(data.id);
      data.ok ? p.resolve(data.result) : p.reject(new Error(data.error.message));
    };
    worker.onerror = (e) => {
      for (const p of pending.values()) p.reject(new Error(e.message || "The Python worker crashed."));
      pending.clear();
    };
  }

  function call(type, payload, transfer = []) {
    if (!worker) start();
    return new Promise((resolve, reject) => {
      const id = nextId++;
      pending.set(id, { resolve, reject });
      worker.postMessage({ id, type, payload }, transfer);
    });
  }

  return {
    /** Start loading Python right away; safe to call twice. */
    init() {
      ready ??= call("init", { base, glue }).then((i) => (info = i));
      return ready;
    },
    get info() {
      return info;
    },
    /** `bytes` is transferred (not copied) to the worker. */
    async load(bytes, dateOrder = null) {
      await this.init();
      return call("load", { bytes, dateOrder }, [bytes]);
    },
    async analyze(options) {
      await this.init();
      return call("analyze", options);
    },
    burn: () => (ready ? call("burn") : Promise.resolve({ ok: true })),
    resources: () => (ready ? call("resources") : Promise.resolve([])),
    terminate() {
      worker?.terminate();
      worker = null;
    },
  };
}
