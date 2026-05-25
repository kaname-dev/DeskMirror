#!/usr/bin/env python3
"""Generate layered glTF for a stereoscopic HOME menu banner (3DS MONITOR)."""

import json
import struct
import zlib
from pathlib import Path

from pixel_font import draw_text

OUT_DIR = Path(__file__).resolve().parent.parent / "resources" / "banner_3d"
W, H = 256, 128


def write_png(path: Path, canvas: list[list[tuple[int, int, int]]]) -> None:
    rows = []
    for row in canvas:
        out = bytearray([0])
        for r, g, b in row:
            out.extend((r, g, b))
        rows.append(bytes(out))
    raw = b"".join(rows)
    compressed = zlib.compress(raw, 9)
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += struct.pack(">I", 13) + b"IHDR" + ihdr + struct.pack(">I", zlib.crc32(b"IHDR" + ihdr) & 0xFFFFFFFF)
    png += struct.pack(">I", len(compressed)) + b"IDAT" + compressed + struct.pack(
        ">I", zlib.crc32(b"IDAT" + compressed) & 0xFFFFFFFF
    )
    png += struct.pack(">I", 0) + b"IEND" + struct.pack(">I", zlib.crc32(b"IEND") & 0xFFFFFFFF)
    path.write_bytes(png)


def make_canvas(bg: tuple[int, int, int]) -> list[list[tuple[int, int, int]]]:
    return [[bg for _ in range(W)] for _ in range(H)]


def draw_layer_back() -> list[list[tuple[int, int, int]]]:
    c = make_canvas((12, 16, 34))
    for y in range(H):
        for x in range(W):
            t = y / max(H - 1, 1)
            c[y][x] = (int(10 + 6 * t), int(14 + 10 * t), int(32 + 16 * t))
    return c


def draw_layer_mid() -> list[list[tuple[int, int, int]]]:
    c = make_canvas((0, 0, 0))
    # PC monitor
    for y in range(52, 109):
        for x in range(28, 99):
            if x < 32 or x > 94 or y < 56 or y > 104:
                c[y][x] = (48, 52, 88)
            else:
                c[y][x] = (58, 205, 178)
    for y in range(72, 89):
        for x in range(104, 129):
            c[y][x] = (255, 145, 48)
    # 3DS shell
    for y in range(54, 109):
        for x in range(138, 229):
            if x < 142 or x > 224 or y < 58 or y > 104:
                c[y][x] = (188, 44, 68)
            elif 150 <= x <= 218 and 62 <= y <= 86:
                c[y][x] = (82, 148, 248)
            elif 158 <= x <= 210 and 90 <= y <= 100:
                c[y][x] = (32, 36, 64)
            else:
                c[y][x] = (188, 44, 68)
    return c


def draw_layer_front() -> list[list[tuple[int, int, int]]]:
    c = make_canvas((0, 0, 0))
    draw_text(c, "3DS MONITOR", 38, 18, (248, 252, 255), scale=3, spacing=2)
    for y in range(52, 56):
        for x in range(30, 226):
            c[y][x] = (255, 150, 55)
    return c


def plane_mesh(z: float, half_w: float, half_h: float) -> dict:
    """XY plane facing +Z (camera looks from +Z)."""
    pos = [
        -half_w, -half_h, z,
        half_w, -half_h, z,
        half_w, half_h, z,
        -half_w, half_h, z,
    ]
    return {
        "positions": pos,
        "uvs": [0.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0],
        "indices": [0, 1, 2, 0, 2, 3],
    }


def build_gltf() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_png(OUT_DIR / "tex_back.png", draw_layer_back())
    write_png(OUT_DIR / "tex_mid.png", draw_layer_mid())
    write_png(OUT_DIR / "tex_front.png", draw_layer_front())

    meshes = [
        plane_mesh(-3.2, 20.0, 11.25),
        plane_mesh(0.0, 20.0, 11.25),
        plane_mesh(3.4, 20.0, 11.25),
    ]
    images = ["tex_back.png", "tex_mid.png", "tex_front.png"]

    buffers_bin = bytearray()
    buffer_views = []
    accessors = []
    meshes_out = []
    materials = []
    textures = []
    images_gltf = []

    def append_data(data: bytes, target: int) -> int:
        offset = len(buffers_bin)
        buffers_bin.extend(data)
        buffer_views.append(
            {
                "buffer": 0,
                "byteOffset": offset,
                "byteLength": len(data),
                "target": target,
            }
        )
        return len(buffer_views) - 1

    for i, (mesh, img_name) in enumerate(zip(meshes, images)):
        pos_bytes = struct.pack(f"<{len(mesh['positions'])}f", *mesh["positions"])
        uv_bytes = struct.pack(f"<{len(mesh['uvs'])}f", *mesh["uvs"])
        idx_bytes = struct.pack(f"<{len(mesh['indices'])}H", *mesh["indices"])

        pos_bv = append_data(pos_bytes, 34962)
        uv_bv = append_data(uv_bytes, 34962)
        idx_bv = append_data(idx_bytes, 34963)

        xs = [mesh["positions"][j] for j in range(0, 12, 3)]
        ys = [mesh["positions"][j] for j in range(1, 12, 3)]
        zs = [mesh["positions"][j] for j in range(2, 12, 3)]
        pos_acc = len(accessors)
        accessors.append(
            {
                "bufferView": pos_bv,
                "componentType": 5126,
                "count": 4,
                "type": "VEC3",
                "min": [min(xs), min(ys), min(zs)],
                "max": [max(xs), max(ys), max(zs)],
            }
        )
        uv_acc = len(accessors)
        accessors.append(
            {
                "bufferView": uv_bv,
                "componentType": 5126,
                "count": 4,
                "type": "VEC2",
            }
        )
        idx_acc = len(accessors)
        accessors.append(
            {
                "bufferView": idx_bv,
                "componentType": 5123,
                "count": 6,
                "type": "SCALAR",
            }
        )

        meshes_out.append(
            {
                "name": f"plane_{i}",
                "primitives": [
                    {
                        "attributes": {"POSITION": pos_acc, "TEXCOORD_0": uv_acc},
                        "indices": idx_acc,
                        "material": i,
                    }
                ]
            }
        )
        images_gltf.append({"uri": img_name})
        textures.append({"source": i})
        materials.append(
            {
                "name": f"mat_{i}",
                "pbrMetallicRoughness": {
                    "baseColorTexture": {"index": i},
                    "metallicFactor": 0.0,
                    "roughnessFactor": 0.9,
                },
                "doubleSided": True,
                "alphaMode": "OPAQUE",
            }
        )

    (OUT_DIR / "banner.bin").write_bytes(buffers_bin)

    gltf = {
        "asset": {"version": "2.0", "generator": "DeskMirror generate_banner_gltf.py"},
        "scene": 0,
        "scenes": [{"nodes": [0, 1, 2]}],
        "nodes": [{"mesh": i} for i in range(3)],
        "meshes": meshes_out,
        "materials": materials,
        "textures": textures,
        "images": images_gltf,
        "buffers": [{"uri": "banner.bin", "byteLength": len(buffers_bin)}],
        "bufferViews": buffer_views,
        "accessors": accessors,
    }

    (OUT_DIR / "banner.gltf").write_text(
        json.dumps(gltf, indent=2), encoding="utf-8"
    )
    print(f"Wrote {OUT_DIR / 'banner.gltf'}")


if __name__ == "__main__":
    build_gltf()
