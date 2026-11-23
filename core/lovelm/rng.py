"""A tiny seeded RNG built only on random.random(), so rerolls are reproducible across Python versions
(random.choice/shuffle/sample have changed between releases; random() has not)."""

from __future__ import annotations

import hashlib
import random


class Rng:
    def __init__(self, seed: int):
        self.seed = seed
        self._r = random.Random(seed)

    def fork(self, label: str) -> "Rng":
        digest = hashlib.sha256(f"{self.seed}:{label}".encode()).hexdigest()
        return Rng(int(digest[:16], 16))

    def random(self) -> float:
        return self._r.random()

    def chance(self, p: float) -> bool:
        return self.random() < p

    def randint(self, a: int, b: int) -> int:
        return a + int(self.random() * (b - a + 1))

    def choice(self, seq):
        return seq[int(self.random() * len(seq))]

    def shuffle(self, items: list) -> None:
        for i in range(len(items) - 1, 0, -1):
            j = int(self.random() * (i + 1))
            items[i], items[j] = items[j], items[i]

    def weighted(self, items, weights):
        x = self.random() * sum(weights)
        for item, w in zip(items, weights):
            x -= w
            if x < 0:
                return item
        return items[-1]
