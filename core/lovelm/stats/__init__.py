"""The stat catalog (docs/STATS.md §1). Importing this package registers every stat."""

from . import effort, events, language, volume  # noqa: F401  (importing registers the stats)
from .base import REGISTRY, Out, Stat, run_all

__all__ = ["REGISTRY", "Out", "Stat", "run_all"]
