"""Draws public/favicon.ico: a gold "play" triangle on a dark rounded square (the film-poster look).
Standard library only; the result is committed, so this only needs re-running if the design changes.

    python3 web/scripts/make-favicon.py
"""
import struct
import zlib
from pathlib import Path

SIZE, SS = 48, 4  # icon size, and supersampling for smooth edges
BG, GOLD = (20, 20, 24), (232, 180, 76)


def inside_rounded_square(x: float, y: float, r: float) -> bool:
    cx, cy = min(max(x, r), SIZE - r), min(max(y, r), SIZE - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def inside_triangle(x: float, y: float) -> bool:
    ax, ay, bx, by, cx, cy = SIZE * 0.36, SIZE * 0.25, SIZE * 0.36, SIZE * 0.75, SIZE * 0.76, SIZE * 0.5
    def side(px, py, qx, qy):  # which side of edge p->q the point is on
        return (x - qx) * (py - qy) - (px - qx) * (y - qy)
    d1, d2, d3 = side(ax, ay, bx, by), side(bx, by, cx, cy), side(cx, cy, ax, ay)
    return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))


rows = []
for py in range(SIZE):
    row = bytearray([0])  # PNG filter byte
    for px in range(SIZE):
        a = g = 0
        for sy in range(SS):
            for sx in range(SS):
                x, y = px + (sx + 0.5) / SS, py + (sy + 0.5) / SS
                if inside_rounded_square(x, y, SIZE * 0.22):
                    a += 1
                    g += inside_triangle(x, y)
        cover = a / (SS * SS)
        t = g / a if a else 0
        rgb = [round(BG[i] + (GOLD[i] - BG[i]) * t) for i in range(3)]
        row += bytes([*rgb, round(255 * cover)])
    rows.append(bytes(row))


def chunk(kind: bytes, data: bytes) -> bytes:
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))


png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0))
       + chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + chunk(b"IEND", b""))
ico = struct.pack("<HHH", 0, 1, 1) + struct.pack("<BBBBHHII", SIZE, SIZE, 0, 0, 1, 32, len(png), 22) + png
out = Path(__file__).resolve().parent.parent / "public" / "favicon.ico"
out.write_bytes(ico)
print(f"wrote {out} ({len(ico)} bytes)")
