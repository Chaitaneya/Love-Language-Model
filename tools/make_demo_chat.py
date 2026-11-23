#!/usr/bin/env python3
"""Generate the demo couple's chat (Rohan & Tara) and its truth sidecar. Deterministic: same seed,
same bytes. Standard library only.

  python3 tools/make_demo_chat.py              write demo/demo_chat.txt and demo/demo_chat.truth.json
  python3 tools/make_demo_chat.py --diagnose   print the measured facts, write nothing
  python3 tools/make_demo_chat.py --check      exit 1 if the committed files differ from a fresh build
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from demo_chat import params as P  # noqa: E402
from demo_chat.build import build, dumps_truth  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "demo"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=P.SEED)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--diagnose", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    demo = build(args.seed)
    chat_bytes = demo.text.encode("utf-8")
    truth_text = dumps_truth(demo.truth)

    if args.diagnose:
        print(json.dumps(demo.truth["measured"], indent=1, ensure_ascii=False, default=str))
        print(f"bytes: {len(chat_bytes):,}  sha256: {hashlib.sha256(chat_bytes).hexdigest()[:16]}")
        return 0
    if args.check:
        same = (args.out / "demo_chat.txt").read_bytes() == chat_bytes and \
               (args.out / "demo_chat.truth.json").read_text(encoding="utf-8") == truth_text
        print("demo files are up to date" if same else "demo files differ from a fresh build")
        return 0 if same else 1

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "demo_chat.txt").write_bytes(chat_bytes)
    (args.out / "demo_chat.truth.json").write_text(truth_text, encoding="utf-8")
    print(f"wrote {args.out}/demo_chat.txt ({len(chat_bytes):,} bytes, {demo.truth['message_count']:,} messages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
