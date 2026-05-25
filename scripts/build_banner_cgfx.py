#!/usr/bin/env python3
"""Build resources/banner.cgfx from banner_3d/banner.gltf via pycgfx."""

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT = SCRIPT_DIR.parent
GLTF = PROJECT / "resources" / "banner_3d" / "banner.gltf"
OUT_CGFX = PROJECT / "resources" / "banner.cgfx"
PYCGFX_REPO = "https://github.com/skyfloogle/pycgfx.git"
PYCGFX_DIR = SCRIPT_DIR / "vendor" / "pycgfx"


def ensure_pycgfx() -> Path:
    main_py = PYCGFX_DIR / "main.py"
    if main_py.exists():
        return main_py
    PYCGFX_DIR.parent.mkdir(parents=True, exist_ok=True)
    print(f"Cloning pycgfx into {PYCGFX_DIR} ...")
    subprocess.run(
        ["git", "clone", "--depth", "1", PYCGFX_REPO, str(PYCGFX_DIR)],
        check=True,
    )
    return main_py


def main() -> int:
    subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "generate_banner_gltf.py")],
        check=True,
    )
    if not GLTF.exists():
        print(f"Missing {GLTF}", file=sys.stderr)
        return 1

    for pkg in ("pillow", "gltflib"):
        try:
            __import__(pkg)
        except ImportError:
            print(f"Installing {pkg} ...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", pkg],
                check=True,
            )

    main_py = ensure_pycgfx()
    print(f"Converting {GLTF} -> {OUT_CGFX} ...")
    subprocess.run(
        [sys.executable, str(main_py), str(GLTF), str(OUT_CGFX)],
        check=True,
        cwd=str(PYCGFX_DIR),
    )
    if not OUT_CGFX.exists():
        print("CGFX output missing", file=sys.stderr)
        return 1
    size = OUT_CGFX.stat().st_size
    print(f"Wrote {OUT_CGFX} ({size} bytes)")
    if size > 0x80000:
        print("WARNING: CGFX exceeds 512KB; 3DS may reject the banner.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
