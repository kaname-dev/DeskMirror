#!/usr/bin/env python3
"""Generate resources/banner.png (256x128) with '3DS MONITOR' title."""

import struct
import zlib
from pathlib import Path

from pixel_font import draw_text, text_size

W, H = 256, 128
OUT = Path(__file__).resolve().parent.parent / "resources" / "banner.png"
TITLE = "3DS MONITOR"


def png_chunk(tag: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)


def base_pixel(x: int, y: int) -> tuple[int, int, int]:
    t = y / max(H - 1, 1)
    r = int(10 + 10 * t)
    g = int(14 + 14 * t)
    b = int(32 + 22 * t)

    # PC monitor
    if 20 <= x <= 88 and 58 <= y <= 114:
        if x < 24 or x > 84 or y < 62 or y > 110:
            r, g, b = 48, 52, 88
        else:
            r, g, b = 58, 205, 178
    elif 94 <= x <= 118 and 78 <= y <= 94:
        r, g, b = 255, 145, 48
    elif 124 <= x <= 214 and 60 <= y <= 114:
        if x < 128 or x > 210 or y < 64 or y > 110:
            r, g, b = 188, 44, 68
        elif 136 <= x <= 206 and 68 <= y <= 92:
            r, g, b = 82, 148, 248
        elif 144 <= x <= 198 and 96 <= y <= 106:
            r, g, b = 32, 36, 64
        else:
            r, g, b = 188, 44, 68
    elif 98 <= x <= 114 and 54 <= y <= 62:
        r, g, b = 255, 205, 85

    return r, g, b


def main() -> None:
    canvas = [[base_pixel(x, y) for x in range(W)] for y in range(H)]

    scale = 3
    spacing = 2
    tw, th = text_size(TITLE, scale=scale, spacing=spacing)
    tx = (W - tw) // 2
    ty = 14
    draw_text(canvas, TITLE, tx, ty, (248, 252, 255), scale=scale, spacing=spacing)

    # Accent underline
    uy = ty + th + 4
    for x in range(tx - 4, tx + tw + 4):
        if 0 <= x < W and 0 <= uy < H:
            canvas[uy][x] = (255, 150, 55)

    rows = []
    for row in canvas:
        out = bytearray([0])
        for r, g, b in row:
            out.extend((r, g, b))
        rows.append(bytes(out))

    raw = b"".join(rows)
    compressed = zlib.compress(raw, 9)
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += png_chunk(b"IHDR", ihdr)
    png += png_chunk(b"IDAT", compressed)
    png += png_chunk(b"IEND", b"")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(png)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
