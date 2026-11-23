"""The only Python the web shell runs besides `lovelm` itself. The worker calls these functions; every
one returns a JSON string: {"ok": true, ...} or {"ok": false, "error": {"code", "message", "data"}}.
The parsed chat stays in this module (in the worker's memory) until burn() or the tab closes."""

import gc
import json
import time

from lovelm import api
from lovelm.errors import LoveLMError

_chat = None


def _default(o):
    if isinstance(o, (set, tuple, frozenset)):
        return list(o)
    return str(o)


def _dumps(obj):
    return json.dumps(obj, ensure_ascii=False, default=_default, separators=(",", ":"))


def _fail(exc):
    if isinstance(exc, LoveLMError):
        return _dumps({"ok": False, "error": {"code": exc.code, "message": str(exc), "data": exc.data}})
    return _dumps({"ok": False, "error": {"code": "internal", "message": f"{type(exc).__name__}: {exc}", "data": {}}})


def load(js_bytes, date_order=None):
    """Parse an uploaded export. `js_bytes` is a JS Uint8Array that never leaves this worker."""
    global _chat
    t0 = time.perf_counter()
    try:
        _chat = None
        data = js_bytes.to_py().tobytes()
        chat = api.load_chat(data, date_order=date_order or None)
        _chat = chat
        meta = chat.meta
        sent = {}
        for m in chat.messages:
            sent[m.sender] = sent.get(m.sender, 0) + 1
        return _dumps({
            "ok": True,
            "ms": round((time.perf_counter() - t0) * 1000),
            "summary": {
                "people": list(chat.participants), "counts": sent, "messages": len(chat.messages),
                "range": [chat.messages[0].ts.date().isoformat(), chat.messages[-1].ts.date().isoformat()],
                "format": meta.family, "date_order": meta.date_order, "hour12": meta.hour12,
                "has_seconds": meta.has_seconds, "warnings": list(chat.warnings),
            },
        })
    except Exception as exc:  # noqa: BLE001 - everything becomes a coded error for the UI
        _chat = None
        return _fail(exc)


def analyze(options_json="{}"):
    """Run every stat and build the poster for the loaded chat."""
    t0 = time.perf_counter()
    try:
        if _chat is None:
            return _dumps({"ok": False, "error": {"code": "no_chat", "message": "No chat is loaded.", "data": {}}})
        o = json.loads(options_json or "{}")
        result = api.analyze(
            _chat, seed=int(o.get("seed", 1234)), spicy=bool(o.get("spicy", False)), quotes=bool(o.get("quotes", True)),
            names=o.get("names") or None, swap=bool(o.get("swap", False)),
        )
        return _dumps({"ok": True, "ms": round((time.perf_counter() - t0) * 1000), "result": result})
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)


def burn():
    """Forget the chat. (The tab closing does the same; this is the 'Burn everything' button.)"""
    global _chat
    _chat = None
    gc.collect()
    return _dumps({"ok": True})
