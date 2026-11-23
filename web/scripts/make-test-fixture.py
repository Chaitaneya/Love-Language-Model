"""Regenerate the JSON fixtures the JavaScript tests read: the demo couple's analysis, plain and Spicy.

    python3 web/scripts/make-test-fixture.py

Run it whenever the core's output changes (test/facts.test.mjs checks a fixture is not stale).
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "core"))

from lovelm.api import analyze, load_chat  # noqa: E402

chat = load_chat((ROOT / "demo" / "demo_chat.txt").read_bytes())
out = ROOT / "web" / "test" / "fixtures"
for name, spicy in (("demo-result.json", False), ("demo-result-spicy.json", True)):
    result = analyze(chat, seed=1234, spicy=spicy, quotes=True)
    (out / name).write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {out / name}")
