#!/usr/bin/env python3
"""Generate DeskMirror icon, banner, and optional splash header."""

import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def main() -> int:
    for name in ("generate_icon.py", "generate_banner.py"):
        script = SCRIPTS / name
        print(f"Running {script.name} ...")
        subprocess.run([sys.executable, str(script)], check=True)
    subprocess.run([sys.executable, str(SCRIPTS / "generate_audio.py")], check=True)
    print("Done. (2D banner.png; for 3D: BANNER_3D=1 make cia after build_banner_cgfx.py)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
