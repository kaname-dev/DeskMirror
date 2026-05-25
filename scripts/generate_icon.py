#!/usr/bin/env python3
"""Generate resources/icon.png (48x48) with '3DS MONITOR' label."""

import struct
import zlib
from pathlib import Path

from pixel_font import draw_text, text_size

W, H = 48, 48
OUT = Path(__file__).resolve().parent.parent / "resources" / "icon.png"
LINE1 = "3DS"
LINE2 = "MONITOR"


def png_chunk(tag: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)


def base_pixel(x: int, y: int) -> tuple[int, int, int]:
    r, g, b = 14, 18, 36

    # 3DS top screen (mini)
    if 14 <= x <= 33 and 6 <= y <= 16:
        if x < 15 or x > 32 or y < 7 or y > 15:
            r, g, b = 188, 44, 68
        else:
            r, g, b = 78, 140, 245
    # bottom screen
    elif 16 <= x <= 31 and 17 <= y <= 22:
        if x < 17 or x > 30 or y < 18 or y > 21:
            r, g, b = 188, 44, 68
        else:
            r, g, b = 34, 38, 62
    # PC screen hint (left)
    elif 4 <= x <= 11 and 8 <= y <= 18:
        if x < 5 or x > 10 or y < 9 or y > 17:
            r, g, b = 50, 54, 86
        else:
            r, g, b = 60, 185, 165
    elif 12 <= x <= 13 and 12 <= y <= 14:
        r, g, b = 255, 140, 48

    return r, g, b


def main() -> None:
    canvas = [[base_pixel(x, y) for x in range(W)] for y in range(H)]

    s1 = 1
    w1, h1 = text_size(LINE1, scale=s1, spacing=0)
    w2, h2 = text_size(LINE2, scale=s1, spacing=0)
    block_h = h1 + h2 + 1
    y0 = H - block_h - 2

    draw_text(canvas, LINE1, (W - w1) // 2, y0, (245, 248, 255), scale=s1, spacing=0)
    draw_text(canvas, LINE2, (W - w2) // 2, y0 + h1 + 1, (255, 168, 72), scale=s1, spacing=0)

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
