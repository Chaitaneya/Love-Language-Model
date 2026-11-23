"""Lets tests import the demo generator (tools/demo_chat) without installing it."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
