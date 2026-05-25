"""Draw Windows mouse cursor onto a captured monitor image."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image


def composite_cursor(img: Image.Image, monitor: dict) -> Image.Image:
    """Overlay cursor; mss does not capture the hardware cursor layer."""
    if sys.platform != "win32":
        return img

    from PIL import ImageDraw
    import ctypes
    from ctypes import wintypes

    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    pt = POINT()
    if not ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
        return img

    x = pt.x - monitor["left"]
    y = pt.y - monitor["top"]
    if x < -24 or y < -24 or x > img.width + 8 or y > img.height + 8:
        return img

    draw = ImageDraw.Draw(img)
    pts = [
        (x, y),
        (x, y + 16),
        (x + 5, y + 11),
        (x + 9, y + 18),
        (x + 12, y + 16),
        (x + 7, y + 10),
        (x + 14, y + 10),
    ]
    draw.polygon(pts, fill=(255, 255, 255), outline=(0, 0, 0))
    return img
