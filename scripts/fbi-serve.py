#!/usr/bin/env python3
"""FBI remote install server with Web UI and QR codes.

Usage:
  python fbi-serve.py --webui              # open dashboard (default without 3DS IP)
  python fbi-serve.py --webui --build
  python fbi-serve.py 192.168.1.23         # one-shot remote install
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import struct
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

ACCEPTED_EXTENSIONS = (".cia", ".tik", ".cetk", ".3dsx")
DEFAULT_PORT = 8080
DEFAULT_UI_PORT = 8765
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_SERVE_DIR = PROJECT_ROOT / "output"
MSYS_BASH = Path(r"C:\msys64\usr\bin\bash.exe")
WEBUI_HTML = SCRIPT_DIR / "fbi-serve-webui.html"
VENDOR_QRCODE_JS = SCRIPT_DIR / "vendor" / "qrcode.min.js"

sys.path.insert(0, str(SCRIPT_DIR))
from qr_render import qr_to_svg  # noqa: E402


def detect_host_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 53))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def run_build() -> None:
    if not MSYS_BASH.exists():
        raise RuntimeError(f"MSYS2 bash not found: {MSYS_BASH}")

    project_posix = str(PROJECT_ROOT).replace("\\", "/")
    if len(project_posix) >= 2 and project_posix[1] == ":":
        project_posix = f"/{project_posix[0].lower()}{project_posix[2:]}"

    cmd = (
        f"source /etc/profile.d/devkit-env.sh && "
        f"cd '{project_posix}' && make cia"
    )
    print("==> Building CIA...")
    result = subprocess.run([str(MSYS_BASH), "-lc", cmd], check=False)
    if result.returncode != 0:
        raise RuntimeError("Build failed (make cia)")


class ServerState:
    def __init__(
        self,
        serve_dir: Path,
        host_ip: str,
        file_port: int,
        ui_port: int,
        single_file: Path | None,
    ) -> None:
        self.serve_dir = serve_dir
        self.host_ip = host_ip
        self.file_port = file_port
        self.ui_port = ui_port
        self.single_file = single_file
        self.lock = threading.Lock()
        self.last_message = ""
        self.last_error = False

    def collect_files(self) -> list[Path]:
        if self.single_file:
            file = self.single_file.resolve()
            if not file.exists():
                raise FileNotFoundError(file)
            if file.suffix.lower() not in ACCEPTED_EXTENSIONS:
                raise ValueError(f"Unsupported extension: {file.suffix}")
            return [file]

        if not self.serve_dir.is_dir():
            raise FileNotFoundError(f"Serve directory not found: {self.serve_dir}")

        files = sorted(
            p.resolve()
            for p in self.serve_dir.iterdir()
            if p.is_file() and p.suffix.lower() in ACCEPTED_EXTENSIONS
        )
        if not files:
            raise FileNotFoundError(
                f"No {', '.join(ACCEPTED_EXTENSIONS)} files in {self.serve_dir}"
            )
        return files

    def fbi_url(self, filename: str) -> str:
        return f"{self.host_ip}:{self.file_port}/{quote(filename)}"

    def http_url(self, filename: str) -> str:
        return f"http://{self.host_ip}:{self.file_port}/{quote(filename)}"

    def web_ui_url(self) -> str:
        return f"http://{self.host_ip}:{self.ui_port}/"

    def build_payload(self, files: list[Path]) -> tuple[str, bytes]:
        lines = [self.fbi_url(file.name) for file in files]
        payload = lines[0] if len(lines) == 1 else "\n".join(lines)
        return payload, payload.encode("ascii")

    def info_dict(self) -> dict:
        try:
            files = self.collect_files()
        except (FileNotFoundError, ValueError) as exc:
            return {
                "host_ip": self.host_ip,
                "file_port": self.file_port,
                "ui_port": self.ui_port,
                "web_ui_url": self.web_ui_url(),
                "serve_dir": str(self.serve_dir),
                "files": [],
                "error": str(exc),
                "last_message": self.last_message,
                "last_error": self.last_error,
            }

        return {
            "host_ip": self.host_ip,
            "file_port": self.file_port,
            "ui_port": self.ui_port,
            "web_ui_url": self.web_ui_url(),
            "serve_dir": str(self.serve_dir),
            "files": [
                {
                    "name": file.name,
                    "size": file.stat().st_size,
                    "fbi_url": self.fbi_url(file.name),
                    "http_url": self.http_url(file.name),
                }
                for file in files
            ],
            "last_message": self.last_message,
            "last_error": self.last_error,
        }

    def send_to_3ds(self, ds_ip: str) -> None:
        files = self.collect_files()
        payload_text, payload_bytes = self.build_payload(files)
        send_urls_to_3ds(ds_ip, payload_bytes)
        with self.lock:
            self.last_message = f"Sent to {ds_ip}: {payload_text}"
            self.last_error = False


def send_urls_to_3ds(target_ip: str, payload: bytes, timeout: float = 120.0) -> None:
    print(f"==> Sending URL(s) to {target_ip}:5000 ...")
    with socket.create_connection((target_ip, 5000), timeout=timeout) as sock:
        sock.sendall(struct.pack("!L", len(payload)) + payload)
        sock.settimeout(timeout)
        while True:
            ack = sock.recv(1)
            if ack:
                break
            time.sleep(0.05)
    print("==> 3DS acknowledged.")


class FileHandler(BaseHTTPRequestHandler):
    state: ServerState

    def log_message(self, fmt: str, *args) -> None:
        print(f"[FILES:{self.state.file_port}] {self.address_string()} - {fmt % args}")

    def do_GET(self) -> None:
        path = unquote(urlparse(self.path).path)
        if path == "/":
            self.send_error(404)
            return

        file_path = (self.state.serve_dir / path.lstrip("/")).resolve()
        try:
            file_path.relative_to(self.state.serve_dir.resolve())
        except ValueError:
            self.send_error(403)
            return

        if not file_path.is_file():
            self.send_error(404)
            return

        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class WebUiHandler(BaseHTTPRequestHandler):
    state: ServerState

    def log_message(self, fmt: str, *args) -> None:
        print(f"[WEBUI:{self.state.ui_port}] {self.address_string()} - {fmt % args}")

    def _send_json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def _send_bytes(self, code: int, content_type: str, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        query = parse_qs(urlparse(self.path).query)

        if path in ("/", "/index.html"):
            if not WEBUI_HTML.is_file():
                self.send_error(500, "Web UI template missing")
                return
            self._send_bytes(200, "text/html; charset=utf-8", WEBUI_HTML.read_bytes())
            return

        if path == "/static/qrcode.min.js":
            if not VENDOR_QRCODE_JS.is_file():
                self.send_error(404)
                return
            self._send_bytes(200, "application/javascript; charset=utf-8", VENDOR_QRCODE_JS.read_bytes())
            return

        if path == "/api/qr":
            text = query.get("text", [""])[0]
            if not text:
                self.send_error(400, "text parameter required")
                return
            try:
                svg = qr_to_svg(text).encode("utf-8")
            except Exception as exc:
                self.send_error(500, f"QR generation failed: {exc}")
                return
            self._send_bytes(200, "image/svg+xml; charset=utf-8", svg)
            return

        if path == "/api/info":
            self._send_json(200, self.state.info_dict())
            return

        self.send_error(404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            body = self._read_json_body()
        except json.JSONDecodeError:
            self._send_json(400, {"ok": False, "message": "Invalid JSON"})
            return

        if path == "/api/send":
            ds_ip = str(body.get("ds_ip", "")).strip()
            if not ds_ip:
                self._send_json(400, {"ok": False, "message": "3DS IP is required"})
                return
            try:
                self.state.send_to_3ds(ds_ip)
            except Exception as exc:
                with self.state.lock:
                    self.state.last_message = str(exc)
                    self.state.last_error = True
                self._send_json(500, {"ok": False, "message": str(exc)})
                return
            self._send_json(200, {"ok": True, "message": self.state.last_message})
            return

        if path == "/api/build":
            try:
                run_build()
                with self.state.lock:
                    self.state.last_message = "Build completed."
                    self.state.last_error = False
                self._send_json(200, {"ok": True, "info": self.state.info_dict()})
            except RuntimeError as exc:
                with self.state.lock:
                    self.state.last_message = str(exc)
                    self.state.last_error = True
                self._send_json(500, {"ok": False, "message": str(exc)})
            return

        self.send_error(404)


def start_servers(state: ServerState) -> tuple[ThreadingHTTPServer, ThreadingHTTPServer]:
    FileHandler.state = state
    WebUiHandler.state = state

    file_server = ThreadingHTTPServer(("0.0.0.0", state.file_port), FileHandler)
    ui_server = ThreadingHTTPServer(("0.0.0.0", state.ui_port), WebUiHandler)

    threading.Thread(target=file_server.serve_forever, daemon=True).start()
    threading.Thread(target=ui_server.serve_forever, daemon=True).start()

    print(f"==> File server : http://{state.host_ip}:{state.file_port}/")
    print(f"==> Web UI      : {state.web_ui_url()}")
    return file_server, ui_server


def run_webui(args: argparse.Namespace) -> int:
    if args.build:
        try:
            run_build()
        except RuntimeError as exc:
            print(exc, file=sys.stderr)
            return 1

    host_ip = args.host_ip or detect_host_ip()
    ui_port = args.ui_port if args.ui_port else DEFAULT_UI_PORT

    state = ServerState(
        serve_dir=args.dir,
        host_ip=host_ip,
        file_port=args.port,
        ui_port=ui_port,
        single_file=args.file,
    )

    try:
        state.collect_files()
    except (FileNotFoundError, ValueError) as exc:
        print(f"Warning: {exc}", file=sys.stderr)

    file_server, ui_server = start_servers(state)

    if args.open_browser:
        webbrowser.open(state.web_ui_url())

    print("Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        file_server.shutdown()
        ui_server.shutdown()
    return 0


def run_oneshot(args: argparse.Namespace) -> int:
    ds_ip = args.ds_ip
    if not ds_ip:
        ds_ip = input("3DS IP (FBI -> Remote Install): ").strip()
    if not ds_ip:
        print("3DS IP is required.", file=sys.stderr)
        return 1

    if args.build:
        try:
            run_build()
        except RuntimeError as exc:
            print(exc, file=sys.stderr)
            return 1

    host_ip = args.host_ip or detect_host_ip()
    state = ServerState(
        serve_dir=args.dir,
        host_ip=host_ip,
        file_port=args.port,
        ui_port=args.ui_port or DEFAULT_UI_PORT,
        single_file=args.file,
    )

    try:
        files = state.collect_files()
        payload_text, payload_bytes = state.build_payload(files)
    except (FileNotFoundError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1

    print("\nFiles:")
    for file in files:
        print(f"  - {file.name}")
    print("\nURLs:")
    print(payload_text)
    print()

    os.chdir(state.serve_dir)
    file_server = ThreadingHTTPServer(("0.0.0.0", state.file_port), FileHandler)
    FileHandler.state = state
    thread = threading.Thread(target=file_server.serve_forever, daemon=True)
    thread.start()

    try:
        send_urls_to_3ds(ds_ip, payload_bytes)
    except OSError as exc:
        print(f"Failed to reach 3DS: {exc}", file=sys.stderr)
        file_server.shutdown()
        return 1

    if args.keep_alive:
        print("HTTP server still running. Press Enter to stop.")
        try:
            input()
        except KeyboardInterrupt:
            pass
    else:
        time.sleep(2)

    file_server.shutdown()
    print("Done.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Serve CIA files to FBI with Web UI and QR codes."
    )
    parser.add_argument(
        "ds_ip",
        nargs="?",
        help="3DS IP for one-shot remote install (omit with --webui)",
    )
    parser.add_argument(
        "--webui",
        action="store_true",
        help="Start Web UI dashboard (default when 3DS IP is omitted)",
    )
    parser.add_argument("--host-ip", help="PC LAN IP (auto-detected if omitted)")
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"CIA file HTTP port (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--ui-port",
        type=int,
        default=DEFAULT_UI_PORT,
        help=f"Web UI port (default: {DEFAULT_UI_PORT})",
    )
    parser.add_argument("--dir", type=Path, default=DEFAULT_SERVE_DIR)
    parser.add_argument("--file", type=Path)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--keep-alive", action="store_true")
    parser.add_argument(
        "--open-browser",
        action="store_true",
        help="Open Web UI in the default browser",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    use_webui = args.webui or not args.ds_ip

    if use_webui and args.ds_ip:
        print("Note: --webui mode ignores positional 3DS IP. Enter it in the dashboard.")
    if use_webui:
        if not args.open_browser:
            args.open_browser = True
        return run_webui(args)
    return run_oneshot(args)


if __name__ == "__main__":
    raise SystemExit(main())
