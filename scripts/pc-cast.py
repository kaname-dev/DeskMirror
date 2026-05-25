#!/usr/bin/env python3
"""Stream PC screen to Nintendo 3DS (DeskMirror homebrew)."""

from __future__ import annotations

import argparse
import json
import socket
import struct
import sys
import time
from pathlib import Path

try:
    import mss
    from PIL import Image
except ImportError:
    print("Missing dependencies. Install with:")
    print("  pip install mss pillow")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR.parent / "cast-config.json"

MAGIC = 0x33504353  # '3PCS'
PORT = 7878
WIDTH = 400
HEIGHT = 240
FRAME_BYTES = WIDTH * HEIGHT * 2
_FRAME_BUFFER = bytearray(FRAME_BYTES)


def rgb_to_565(r: int, g: int, b: int) -> int:
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)


def bgra_to_rgb565(bgra: bytes, width: int, height: int, out: bytearray | None = None) -> bytes:
    """Fast path: mss screenshot (BGRA) -> RGB565 without PIL resize."""
    buf = out if out is not None and len(out) == FRAME_BYTES else bytearray(FRAME_BYTES)
    j = 0
    for i in range(0, width * height * 4, 4):
        b = bgra[i]
        g = bgra[i + 1]
        r = bgra[i + 2]
        v = rgb_to_565(r, g, b)
        buf[j] = v & 0xFF
        buf[j + 1] = (v >> 8) & 0xFF
        j += 2
    return bytes(buf)


def frame_to_rgb565(img: Image.Image, out: bytearray | None = None) -> bytes:
    # 3DS top screen: 400x240 RGB565 (full quality, no compression)
    if img.size != (WIDTH, HEIGHT):
        img = img.convert("RGB").resize((WIDTH, HEIGHT), Image.Resampling.NEAREST)
    else:
        img = img.convert("RGB")
    buf = out if out is not None and len(out) == FRAME_BYTES else bytearray(FRAME_BYTES)
    i = 0
    px = img.load()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            r, g, b = px[x, y]
            v = rgb_to_565(r, g, b)
            buf[i] = v & 0xFF
            buf[i + 1] = (v >> 8) & 0xFF
            i += 2
    return bytes(buf)


def find_primary_index(monitors: list[dict]) -> int:
    for idx, mon in enumerate(monitors[1:], start=1):
        if mon["left"] == 0 and mon["top"] == 0:
            return idx
    return 1


def pick_extended_index(monitors: list[dict]) -> int:
    if len(monitors) <= 2:
        return 1

    primary = find_primary_index(monitors)
    others = [idx for idx in range(1, len(monitors)) if idx != primary]
    if not others:
        return 1
    if len(others) == 1:
        return others[0]
    return max(others, key=lambda i: monitors[i]["left"])


def resolve_monitor_index(
    sct: mss.mss,
    monitor: int | None,
    use_primary: bool,
    use_vdd: bool,
    monitor_keyword: str | None,
) -> int:
    if use_primary:
        return 1
    if monitor is not None and 0 < monitor < len(sct.monitors):
        return monitor

    if use_vdd and sys.platform == "win32":
        from win_display import pick_virtual_mss_index

        vdd_idx = pick_virtual_mss_index(sct.monitors, monitor_keyword)
        if vdd_idx is not None:
            return vdd_idx
        print(
            "Virtual monitor not found. Run scripts\\setup-virtual-monitor.ps1",
            file=sys.stderr,
        )
        print("Falling back to extended (non-primary) display.", file=sys.stderr)

    if monitor is not None:
        print(f"Warning: monitor {monitor} not found, using auto.", file=sys.stderr)
    return pick_extended_index(sct.monitors)


def describe_monitor(monitors: list[dict], index: int) -> str:
    mon = monitors[index]
    primary = find_primary_index(monitors)
    role = "primary" if index == primary else "extended"
    extra = ""
    if sys.platform == "win32":
        try:
            from win_display import attach_mss_indices, list_windows_displays

            displays = list_windows_displays()
            attach_mss_indices(displays, monitors)
            for d in displays:
                if d.mss_index == index:
                    tag = "virtual" if d.is_virtual else "physical"
                    extra = f" | {d.device_string} [{tag}]"
                    break
        except Exception:
            pass
    return (
        f"#{index} {mon['width']}x{mon['height']} "
        f"@ ({mon['left']},{mon['top']}) [{role}]{extra}"
    )


def list_monitors() -> None:
    with mss.mss() as sct:
        print("Available monitors (mss index):")
        for idx in range(1, len(sct.monitors)):
            print(f"  {describe_monitor(sct.monitors, idx)}")
        print(f"Auto extended pick: #{pick_extended_index(sct.monitors)}")
        if sys.platform == "win32":
            from win_display import pick_virtual_mss_index

            vdd = pick_virtual_mss_index(sct.monitors, None)
            if vdd is not None:
                print(f"Auto virtual (3DS monitor) pick: #{vdd}")
            else:
                print("Auto virtual (3DS monitor) pick: (none - install virtual display driver)")


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Warning: invalid {CONFIG_PATH}: {exc}", file=sys.stderr)
        return {}


def capture_monitor(
    sct: mss.mss, monitor_index: int, show_cursor: bool = True
) -> tuple[Image.Image | None, bytes | None]:
    """Returns (pil_image, raw_rgb565). rgb565 set when native 400x240 fast path used."""
    mon = sct.monitors[monitor_index]
    shot = sct.grab(mon)
    if shot.width == WIDTH and shot.height == HEIGHT and not show_cursor:
        return None, bgra_to_rgb565(shot.bgra, WIDTH, HEIGHT, _FRAME_BUFFER)
    img = Image.frombytes("RGB", shot.size, shot.rgb)
    if show_cursor:
        from win_cursor import composite_cursor

        img = composite_cursor(img, mon)
    return img, None


def send_frame(sock: socket.socket, payload: bytes) -> None:
    header = struct.pack("<IHH", MAGIC, WIDTH, HEIGHT)
    sock.sendall(header)
    sock.sendall(payload)


def connect(host: str, port: int) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 256 * 1024)
    print(f"Connecting to {host}:{port} ...")
    sock.connect((host, port))
    print("Connected. Streaming (Ctrl+C to stop).")
    return sock


def main() -> int:
    cfg = load_config()

    parser = argparse.ArgumentParser(
        description="PC screen cast sender for 3DS (DeskMirror)",
    )
    parser.add_argument("--host", default=cfg.get("host"), help="3DS IP address")
    parser.add_argument("--port", type=int, default=cfg.get("port", PORT))
    parser.add_argument(
        "--fps",
        type=float,
        default=cfg.get("fps", 25.0),
        help="Target FPS (0 = uncapped). Quality stays 400x240 RGB565.",
    )
    parser.add_argument("--monitor", type=int, default=cfg.get("monitor"))
    parser.add_argument(
        "--primary",
        action="store_true",
        default=cfg.get("primary", False),
        help="Capture primary display (duplicate mode)",
    )
    parser.add_argument(
        "--vdd",
        action="store_true",
        default=cfg.get("vdd", False),
        help="Capture Windows virtual monitor (3DS as extended display)",
    )
    parser.add_argument(
        "--monitor-name",
        default=cfg.get("monitor_keyword"),
        help="Substring match for monitor name (with --vdd)",
    )
    parser.add_argument("--list-monitors", action="store_true")
    parser.add_argument(
        "--no-cursor",
        action="store_true",
        default=cfg.get("no_cursor", False),
        help="Do not draw mouse cursor on stream",
    )
    args = parser.parse_args()

    if args.list_monitors:
        list_monitors()
        return 0

    if not args.host:
        parser.error("--host is required (3DS IP shown on the bottom screen)")

    with mss.mss() as sct:
        monitor_index = resolve_monitor_index(
            sct,
            args.monitor,
            args.primary,
            args.vdd,
            args.monitor_name,
        )
        mode = "virtual monitor" if args.vdd else ("primary" if args.primary else "extended")
        print(f"Capture ({mode}): {describe_monitor(sct.monitors, monitor_index)}")

    uncapped = args.fps <= 0
    interval = 0.0 if uncapped else (1.0 / args.fps)
    if uncapped:
        print("FPS: uncapped (400x240 full quality)")
    else:
        print(f"FPS target: {args.fps:g} (400x240 full quality)")
    sent = 0
    t0 = time.perf_counter()

    while True:
        try:
            sock = connect(args.host, args.port)
        except OSError as e:
            print(f"Connection failed: {e}")
            print("Retrying in 2s ... (check 3DS app is running)")
            time.sleep(2)
            continue

        try:
            with mss.mss() as sct:
                monitor_index = resolve_monitor_index(
                    sct,
                    args.monitor,
                    args.primary,
                    args.vdd,
                    args.monitor_name,
                )
                while True:
                    loop_start = time.perf_counter()
                    img, payload = capture_monitor(
                        sct, monitor_index, show_cursor=not args.no_cursor
                    )
                    if payload is None:
                        payload = frame_to_rgb565(img, _FRAME_BUFFER)
                    send_frame(sock, payload)
                    sent += 1

                    elapsed = time.perf_counter() - t0
                    if elapsed >= 1.0:
                        print(f"\r{sent} fps", end="", flush=True)
                        sent = 0
                        t0 = time.perf_counter()

                    spent = time.perf_counter() - loop_start
                    sleep_for = interval - spent
                    if sleep_for > 0:
                        time.sleep(sleep_for)
        except KeyboardInterrupt:
            print("\nStopped.")
            return 0
        except OSError as e:
            print(f"\nDisconnected: {e}")
            sock.close()
            print("Reconnecting in 2s ...")
            time.sleep(2)


if __name__ == "__main__":
    raise SystemExit(main())
