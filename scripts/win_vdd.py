"""Virtual Display Driver (VDD) control on Windows."""

from __future__ import annotations

import ctypes
import re
import subprocess
import sys
import time
from pathlib import Path

if sys.platform != "win32":
    raise RuntimeError("win_vdd is Windows-only")

PIPE_NAME = r"\\.\pipe\MTTVirtualDisplayPipe"
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
VDD_XML = Path(r"C:\VirtualDisplayDriver\vdd_settings.xml")
PROJECT_VDD_XML = Path(__file__).resolve().parent.parent / "resources" / "windows" / "vdd_settings.xml"
PNP_ELEVATE_PS1 = Path(__file__).resolve().parent / "vdd-pnp-elevate.ps1"

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
ERROR_BROKEN_PIPE = 109
PIPE_READMODE_MESSAGE = 0x00000002

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.WaitNamedPipeW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32]
kernel32.WaitNamedPipeW.restype = ctypes.c_int
kernel32.CreateFileW.argtypes = [
    ctypes.c_wchar_p,
    ctypes.c_uint32,
    ctypes.c_uint32,
    ctypes.c_void_p,
    ctypes.c_uint32,
    ctypes.c_uint32,
    ctypes.c_void_p,
]
kernel32.CreateFileW.restype = ctypes.c_void_p
kernel32.SetNamedPipeHandleState.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_uint32),
    ctypes.POINTER(ctypes.c_uint32),
    ctypes.POINTER(ctypes.c_uint32),
]
kernel32.SetNamedPipeHandleState.restype = ctypes.c_int
kernel32.WriteFile.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_uint32,
    ctypes.POINTER(ctypes.c_uint32),
    ctypes.c_void_p,
]
kernel32.WriteFile.restype = ctypes.c_int
kernel32.ReadFile.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_uint32,
    ctypes.POINTER(ctypes.c_uint32),
    ctypes.c_void_p,
]
kernel32.ReadFile.restype = ctypes.c_int
kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
kernel32.CloseHandle.restype = ctypes.c_int


class VddError(OSError):
    """VDD control error."""


def _set_xml_monitor_count(count: int) -> None:
    if not VDD_XML.parent.exists():
        VDD_XML.parent.mkdir(parents=True, exist_ok=True)
    if VDD_XML.exists():
        text = VDD_XML.read_text(encoding="utf-8")
        if re.search(r"<count>\s*\d+\s*</count>", text):
            text = re.sub(
                r"(<count>)\s*\d+\s*(</count>)",
                rf"\g<1>{count}\g<2>",
                text,
                count=1,
            )
        else:
            text = text.replace(
                "<monitors>",
                f"<monitors>\n        <count>{count}</count>",
                1,
            )
        VDD_XML.write_text(text, encoding="utf-8")
    elif PROJECT_VDD_XML.exists():
        text = PROJECT_VDD_XML.read_text(encoding="utf-8")
        text = re.sub(
            r"(<count>)\s*\d+\s*(</count>)",
            rf"\g<1>{count}\g<2>",
            text,
            count=1,
        )
        VDD_XML.write_text(text, encoding="utf-8")
    else:
        raise VddError(f"Missing VDD config: {VDD_XML}")


def _run_pnp(action: str) -> None:
    if not PNP_ELEVATE_PS1.exists():
        raise VddError(f"Missing script: {PNP_ELEVATE_PS1}")
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PNP_ELEVATE_PS1),
            "-Action",
            action,
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.stdout:
        print(proc.stdout.strip())
    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "PnP toggle failed").strip()
        if "canceled" in msg.lower() or proc.returncode == 1223:
            raise VddError("Administrator approval was canceled (UAC).")
        raise VddError(msg)


def _open_pipe(wait_ms: int = 10_000) -> int:
    if not kernel32.WaitNamedPipeW(PIPE_NAME, wait_ms):
        raise VddError(
            ctypes.get_last_error(),
            "VDD pipe not available",
        )
    handle = kernel32.CreateFileW(
        PIPE_NAME,
        GENERIC_READ | GENERIC_WRITE,
        0,
        None,
        OPEN_EXISTING,
        0,
        None,
    )
    if handle in (None, INVALID_HANDLE_VALUE):
        raise VddError(ctypes.get_last_error(), "Failed to open VDD pipe")
    mode = ctypes.c_uint32(PIPE_READMODE_MESSAGE)
    kernel32.SetNamedPipeHandleState(
        handle,
        ctypes.byref(mode),
        None,
        None,
    )
    return handle


def send_command(cmd: str, *, wait_ms: int = 10_000) -> bytes:
    handle = _open_pipe(wait_ms)
    try:
        payload = cmd.encode("utf-16-le")
        written = ctypes.c_uint32(0)
        if not kernel32.WriteFile(
            handle,
            payload,
            len(payload),
            ctypes.byref(written),
            None,
        ):
            raise VddError(ctypes.get_last_error(), f"WriteFile failed: {cmd}")

        chunks: list[bytes] = []
        buf = (ctypes.c_char * 4096)()
        while True:
            n = ctypes.c_uint32(0)
            ok = kernel32.ReadFile(
                handle,
                buf,
                4096,
                ctypes.byref(n),
                None,
            )
            if not ok:
                err = ctypes.get_last_error()
                if err in (0, ERROR_BROKEN_PIPE):
                    break
                raise VddError(err, "ReadFile failed")
            if n.value == 0:
                break
            chunks.append(bytes(buf[: n.value]))
        return b"".join(chunks)
    finally:
        kernel32.CloseHandle(handle)


def ping() -> bool:
    try:
        return b"PONG" in send_command("PING", wait_ms=5000)
    except OSError:
        return False


def set_display_count(count: int) -> None:
    if count < 0 or count > 16:
        raise ValueError("display count must be 0-16")
    send_command(f"SETDISPLAYCOUNT {count}", wait_ms=60_000)


def enable() -> None:
    """Turn on VDD: xml count=1, enable adapter (UAC), optional pipe reload."""
    _set_xml_monitor_count(1)
    _run_pnp("enable")
    time.sleep(2.0)
    if ping():
        try:
            set_display_count(1)
        except VddError:
            pass


def disable() -> None:
    """Turn off VDD: xml count=0, disable adapter (UAC)."""
    _set_xml_monitor_count(0)
    try:
        if ping():
            set_display_count(0)
            time.sleep(2.0)
    except VddError:
        pass
    _run_pnp("disable")


def wait_for_virtual_monitor(
    keyword: str | None = None,
    *,
    timeout: float = 30.0,
    poll_interval: float = 0.5,
) -> int | None:
    import mss

    from win_display import pick_virtual_mss_index

    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        with mss.mss() as sct:
            idx = pick_virtual_mss_index(sct.monitors, keyword)
            if idx is not None:
                return idx
        time.sleep(poll_interval)
    return None
