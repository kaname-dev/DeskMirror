"""SVG QR code rendering (stdlib + Nayuki qrcodegen)."""

from __future__ import annotations

import sys
from pathlib import Path

_VENDOR = Path(__file__).resolve().parent / "vendor"
if str(_VENDOR) not in sys.path:
    sys.path.insert(0, str(_VENDOR))

from qrcodegen import QrCode  # noqa: E402


def qr_to_svg(text: str, border: int = 4, scale: int = 8) -> str:
    qr = QrCode.encode_text(text, QrCode.Ecc.MEDIUM)
    size = qr.get_size()
    dim = (size + border * 2) * scale
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {dim} {dim}" '
            f'width="{dim}" height="{dim}">'
        ),
        f'<rect width="100%" height="100%" fill="#ffffff"/>',
    ]
    for y in range(size):
        for x in range(size):
            if qr.get_module(x, y):
                px = (x + border) * scale
                py = (y + border) * scale
                lines.append(
                    f'<rect x="{px}" y="{py}" width="{scale}" height="{scale}" fill="#000000"/>'
                )
    lines.append("</svg>")
    return "\n".join(lines)
