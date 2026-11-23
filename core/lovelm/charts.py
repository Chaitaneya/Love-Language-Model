"""Data for the Director's Cut charts (docs/PRD.md §8). Plain numbers; the browser draws them."""

from __future__ import annotations

from bisect import bisect_right

from .context import A, B, Ctx

REPLY_EDGES = [10, 30, 60, 120, 300, 600, 1800, 3600, 10800]  # seconds; last bucket is everything slower
REPLY_LABELS = ["<10s", "10-30s", "30-60s", "1-2m", "2-5m", "5-10m", "10-30m", "30m-1h", "1-3h", "3h+"]


def charts(c: Ctx) -> dict:
    months: list[str] = []
    ym = (c.first_date().year, c.first_date().month)
    end = (c.last_date().year, c.last_date().month)
    while ym <= end:
        months.append(f"{ym[0]}-{ym[1]:02d}")
        ym = (ym[0] + (ym[1] == 12), ym[1] % 12 + 1)
    idx = {m: i for i, m in enumerate(months)}
    heartbeat = {A: [0] * len(months), B: [0] * len(months)}
    heat = [[0] * 24 for _ in range(7)]
    for i, m in enumerate(c.msgs):
        heartbeat[c.side[i]][idx[f"{m.ts.year}-{m.ts.month:02d}"]] += 1
        heat[m.ts.weekday()][m.ts.hour] += 1
    hist = {s: [0] * (len(REPLY_EDGES) + 1) for s in (A, B)}
    for s in (A, B):
        for sec in c.replies[s]:
            hist[s][bisect_right(REPLY_EDGES, sec)] += 1
    return {
        "heartbeat": {"months": months, "A": heartbeat[A], "B": heartbeat[B],
                      "total": [x + y for x, y in zip(heartbeat[A], heartbeat[B])]},
        "heatmap": {"rows": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], "cells": heat},
        "reply_hist": {"labels": REPLY_LABELS, "A": hist[A], "B": hist[B]},
        "hours": {"A": c.hour_by[A], "B": c.hour_by[B]},
    }
