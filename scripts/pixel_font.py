"""Minimal 5x7 pixel font for asset generators."""

from __future__ import annotations

# fmt: off
GLYPHS: dict[str, list[str]] = {
    " ": ["     ", "     ", "     ", "     ", "     ", "     ", "     "],
    "3": [" ### ", "    #", "  ## ", "    #", " ### ", "     ", "     "],
    "D": [" ##  ", " # # ", " # # ", " # # ", " ##  ", "     ", "     "],
    "S": ["  ## ", " #   ", "  #  ", "   # ", " ##  ", "     ", "     "],
    "M": [" # # ", " ### ", " # # ", " # # ", " # # ", "     ", "     "],
    "O": [" ### ", " # # ", " # # ", " # # ", " ### ", "     ", "     "],
    "N": [" # # ", " ### ", " ### ", " # # ", " # # ", "     ", "     "],
    "I": [" ### ", "  #  ", "  #  ", "  #  ", " ### ", "     ", "     "],
    "T": [" ### ", "  #  ", "  #  ", "  #  ", "  #  ", "     ", "     "],
    "E": [" ### ", " #   ", " ##  ", " #   ", " ### ", "     ", "     "],
    "R": [" ##  ", " # # ", " ##  ", " # # ", " # # ", "     ", "     "],
}
# fmt: on

FONT_W = 5
FONT_H = 7


def text_size(text: str, scale: int = 1, spacing: int = 1) -> tuple[int, int]:
    n = len(text)
    if n == 0:
        return 0, 0
    w = n * FONT_W * scale + (n - 1) * spacing
    h = FONT_H * scale
    return w, h


def draw_text(
    canvas: list[list[tuple[int, int, int]]],
    text: str,
    x0: int,
    y0: int,
    color: tuple[int, int, int],
    *,
    scale: int = 1,
    spacing: int = 1,
) -> None:
    h = len(canvas)
    w = len(canvas[0]) if h else 0
    cx = x0
    for ch in text.upper():
        glyph = GLYPHS.get(ch, GLYPHS[" "])
        for gy, row in enumerate(glyph):
            for gx, c in enumerate(row):
                if c != "#":
                    continue
                for sy in range(scale):
                    for sx in range(scale):
                        px = cx + gx * scale + sx
                        py = y0 + gy * scale + sy
                        if 0 <= px < w and 0 <= py < h:
                            canvas[py][px] = color
        cx += FONT_W * scale + spacing
