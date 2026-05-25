#!/usr/bin/env python3
"""Generate resources/icon.png (48x48) for DeskMirror."""

import struct
import zlib
from pathlib import Path

W, H = 48, 48
OUT = Path(__file__).resolve().parent.parent / "resources" / "icon.png"


def png_chunk(tag: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)


def main() -> None:
    rows = []
    for y in range(H):
        row = bytearray([0])
        for x in range(W):
            # PC monitor (left)
            if 3 <= x <= 20 and 8 <= y <= 26:
                if x < 5 or x > 18 or y < 10 or y > 24:
                    r, g, b = 55, 58, 90
                else:
                    r, g, b = 72, 200, 180
            # Arrow
            elif 22 <= x <= 28 and 17 <= y <= 21:
                r, g, b = 255, 140, 50
            elif x == 29 and 18 <= y <= 20:
                r, g, b = 255, 140, 50
            # 3DS top screen
            elif 31 <= x <= 44 and 9 <= y <= 22:
                if x < 32 or x > 43 or y < 10 or y > 21:
                    r, g, b = 200, 50, 70
                else:
                    r, g, b = 90, 160, 255
            # 3DS bottom screen
            elif 33 <= x <= 42 and 26 <= y <= 34:
                if x < 34 or x > 41 or y < 27 or y > 33:
                    r, g, b = 200, 50, 70
                else:
                    r, g, b = 40, 44, 72
            # Wi-Fi arcs
            elif 10 <= y <= 6 and 24 <= x <= 36:
                r, g, b = 255, 200, 80
            elif (x - 12) ** 2 + (y - 32) ** 2 < 20 and y >= 30:
                r, g, b = 255, 200, 80
            else:
                r, g, b = 14, 18, 36
            row.extend((r, g, b))
        rows.append(bytes(row))

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
