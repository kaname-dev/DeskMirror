"""Windows display enumeration (maps to mss monitor indices)."""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from dataclasses import dataclass

if sys.platform != "win32":
    raise RuntimeError("win_display is Windows-only")

user32 = ctypes.windll.user32

DISPLAY_DEVICE_ATTACHED_TO_DESKTOP = 0x1

VDD_KEYWORDS = (
    "virtual",
    "idd",
    "desk mirror",
    "deskmirror",
    "indirect",
    "parsec",
    "usb mobile",
    "miri",
    "vdd",
)


class DISPLAY_DEVICEW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("DeviceName", wintypes.WCHAR * 32),
        ("DeviceString", wintypes.WCHAR * 128),
        ("StateFlags", wintypes.DWORD),
        ("DeviceID", wintypes.WCHAR * 128),
        ("DeviceKey", wintypes.WCHAR * 128),
    ]


class DEVMODEW(ctypes.Structure):
    _fields_ = [
        ("dmDeviceName", wintypes.WCHAR * 32),
        ("dmSpecVersion", wintypes.WORD),
        ("dmDriverVersion", wintypes.WORD),
        ("dmSize", wintypes.WORD),
        ("dmDriverExtra", wintypes.WORD),
        ("dmFields", wintypes.DWORD),
        ("dmOrientation", wintypes.SHORT),
        ("dmPaperSize", wintypes.SHORT),
        ("dmPaperLength", wintypes.SHORT),
        ("dmPaperWidth", wintypes.SHORT),
        ("dmScale", wintypes.SHORT),
        ("dmCopies", wintypes.SHORT),
        ("dmDefaultSource", wintypes.SHORT),
        ("dmPrintQuality", wintypes.SHORT),
        ("dmColor", wintypes.SHORT),
        ("dmDuplex", wintypes.SHORT),
        ("dmYResolution", wintypes.SHORT),
        ("dmTTOption", wintypes.SHORT),
        ("dmCollate", wintypes.SHORT),
        ("dmFormName", wintypes.WCHAR * 32),
        ("dmLogPixels", wintypes.WORD),
        ("dmBitsPerPel", wintypes.DWORD),
        ("dmPelsWidth", wintypes.DWORD),
        ("dmPelsHeight", wintypes.DWORD),
        ("dmDisplayFlags", wintypes.DWORD),
        ("dmDisplayFrequency", wintypes.DWORD),
        ("dmICMMethod", wintypes.DWORD),
        ("dmICMIntent", wintypes.DWORD),
        ("dmMediaType", wintypes.DWORD),
        ("dmDitherType", wintypes.DWORD),
        ("dmReserved1", wintypes.DWORD),
        ("dmReserved2", wintypes.DWORD),
        ("dmPanningWidth", wintypes.DWORD),
        ("dmPanningHeight", wintypes.DWORD),
    ]


@dataclass
class WinDisplay:
    device_name: str
    device_string: str
    left: int
    top: int
    width: int
    height: int
    is_virtual: bool
    mss_index: int | None = None


def _enum_attached_displays() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    idx = 0
    while True:
        dev = DISPLAY_DEVICEW()
        dev.cb = ctypes.sizeof(DISPLAY_DEVICEW)
        if not user32.EnumDisplayDevicesW(None, idx, ctypes.byref(dev), 0):
            break
        if dev.StateFlags & DISPLAY_DEVICE_ATTACHED_TO_DESKTOP:
            out.append((dev.DeviceName, dev.DeviceString))
        idx += 1
    return out


def _display_rect(device_name: str) -> tuple[int, int, int, int] | None:
    dm = DEVMODEW()
    dm.dmSize = ctypes.sizeof(DEVMODEW)
    if not user32.EnumDisplaySettingsW(device_name, -1, ctypes.byref(dm)):
        return None
    dm.dmFields = 0x00080000 | 0x00100000  # DM_PELSWIDTH | DM_PELSHEIGHT
    if not user32.EnumDisplaySettingsW(device_name, -1, ctypes.byref(dm)):
        return None
    pos_dm = DEVMODEW()
    pos_dm.dmSize = ctypes.sizeof(DEVMODEW)
    user32.EnumDisplaySettingsW(device_name, -1, ctypes.byref(pos_dm))
    # Position from dmPosition if available; fallback to EnumDisplayMonitors via mss later
    left = getattr(pos_dm, "dmPosition", None)
    # DEVMODEW on Windows has dmPosition only in newer SDK - use MonitorFromPoint alternative

    # Use EnumDisplaySettingsEx - simpler: grab from mss matching by size first pass
    width = int(dm.dmPelsWidth)
    height = int(dm.dmPelsHeight)
    return (0, 0, width, height)  # position filled by mss match


def list_windows_displays() -> list[WinDisplay]:
    displays: list[WinDisplay] = []
    for device_name, device_string in _enum_attached_displays():
        dm = DEVMODEW()
        dm.dmSize = ctypes.sizeof(DEVMODEW)
        if not user32.EnumDisplaySettingsW(device_name, -1, ctypes.byref(dm)):
            continue
        width = int(dm.dmPelsWidth)
        height = int(dm.dmPelsHeight)
        blob = f"{device_string} {device_name}".lower()
        is_virtual = any(k in blob for k in VDD_KEYWORDS)
        displays.append(
            WinDisplay(
                device_name=device_name,
                device_string=device_string,
                left=0,
                top=0,
                width=width,
                height=height,
                is_virtual=is_virtual,
            )
        )
    return displays


def attach_mss_indices(displays: list[WinDisplay], mss_monitors: list[dict]) -> None:
    used: set[int] = set()
    for disp in displays:
        best_idx = None
        best_score = -1
        for idx in range(1, len(mss_monitors)):
            if idx in used:
                continue
            m = mss_monitors[idx]
            if m["width"] == disp.width and m["height"] == disp.height:
                score = 1000
            else:
                score = -abs(m["width"] - disp.width) - abs(m["height"] - disp.height)
            if score > best_score:
                best_score = score
                best_idx = idx
        if best_idx is not None:
            disp.mss_index = best_idx
            disp.left = mss_monitors[best_idx]["left"]
            disp.top = mss_monitors[best_idx]["top"]
            used.add(best_idx)


def pick_virtual_mss_index(
    mss_monitors: list[dict],
    keyword: str | None = None,
) -> int | None:
    displays = list_windows_displays()
    attach_mss_indices(displays, mss_monitors)

    if keyword:
        key = keyword.lower()
        for d in displays:
            if key in d.device_string.lower() or key in d.device_name.lower():
                if d.mss_index is not None:
                    return d.mss_index

    virtuals = [d for d in displays if d.is_virtual and d.mss_index is not None]
    if not virtuals:
        return None

    # Prefer resolution close to 3DS top screen aspect (5:3)
    target_aspect = 400 / 240

    def aspect_score(d: WinDisplay) -> float:
        aspect = d.width / max(d.height, 1)
        return -abs(aspect - target_aspect)

    best = max(virtuals, key=aspect_score)
    return best.mss_index


def format_display_line(d: WinDisplay) -> str:
    role = "virtual" if d.is_virtual else "physical"
    idx = d.mss_index if d.mss_index is not None else "?"
    return (
        f"mss #{idx}  {d.width}x{d.height} @ ({d.left},{d.top})  "
        f"[{role}]  {d.device_string}"
    )
