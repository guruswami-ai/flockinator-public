"""Wall tiles: split one graphic into addressed per-node tiles.

The coordinator-side companion to the mission slate (issue #89).
Given one wall graphic (the slate, or any unified-wall image), this
produces the 16 tile payloads a coordinator pushes to individual
nodes before/after a mission, each with placement and a sha256, so
a node can verify the tile it received and the wall can be audited
from the camera afterwards.

Geometry (matches wall_report): tiles are TILE_PX x TILE_PX panel
pixels; the wall is 4x4 = 256x256 for the default 64. Node names are
fleet coordinates: rows top->bottom D,C,B,A, columns 1..4. Because
the camera sees the panels from behind, the default is to flip the
source horizontally before tiling (flip_horizontal=True) so text
and QR codes read correctly from the front; the manifest records
exactly what was done - no silent orientation decisions.

A QR spanning the wall is split like any other graphic: each tile
carries its module block, quiet zone included in the source. Keep
the source QR <= version 8 (see slate.py) so modules survive.

Input: PNG/JPG via Pillow (optional dep), or binary PPM (P6) with
the stdlib path. Output tiles are written in the input's format
family (PNG when Pillow is present, else PPM).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from .wall_observer import file_sha256, utc_iso

TILE_PX = 64
ROWS = ("D", "C", "B", "A")
COLS = ("1", "2", "3", "4")


def node_at(row: int, col: int) -> str:
    return f"{ROWS[row]}{COLS[col]}"


def tile_positions(tile_px: int = TILE_PX) -> list[dict]:
    """All 16 tile placements in wall order (top-left first)."""
    pos = []
    for r in range(4):
        for c in range(4):
            pos.append({"node": node_at(r, c), "row": r, "col": c,
                        "x": c * tile_px, "y": r * tile_px,
                        "w": tile_px, "h": tile_px})
    return pos


def read_ppm(data: bytes):
    """Minimal binary PPM (P6, maxval 255) reader -> (pixels, w, h)."""
    parts = data.split(b"\n", 3)
    if len(parts) < 4 or parts[0].strip() != b"P6":
        raise ValueError("not a binary PPM (P6)")
    w, h = (int(v) for v in parts[1].split())
    if int(parts[2]) != 255:
        raise ValueError("PPM maxval must be 255")
    raw = parts[3]
    if len(raw) < w * h * 3:
        raise ValueError("truncated PPM pixel data")
    pixels = [[tuple(raw[(y * w + x) * 3:(y * w + x) * 3 + 3])
               for x in range(w)] for y in range(h)]
    return pixels, w, h


def write_ppm(path, pixels, w: int, h: int) -> None:
    body = bytearray()
    for y in range(h):
        for x in range(w):
            body += bytes(pixels[y][x])
    Path(path).write_bytes(f"P6\n{w} {h}\n255\n".encode() + bytes(body))


def _load_pixels(path):
    p = Path(path)
    if p.suffix.lower() == ".ppm":
        return read_ppm(p.read_bytes())
    from PIL import Image
    im = Image.open(p).convert("RGB")
    w, h = im.size
    px = im.load()
    return [[px[x, y] for x in range(w)] for y in range(h)], w, h


def split_graphic(image_path, out_dir, tile_px: int = TILE_PX,
                  flip_horizontal: bool = True) -> dict:
    """Split a wall graphic into 16 addressed tiles + manifest.json.

    The source is resized/cropped by the caller to 4*tile_px square;
    anything else is an error rather than a silent distortion (a QR
    with non-uniform scaling may not decode).
    """
    pixels, w, h = _load_pixels(image_path)
    expect = 4 * tile_px
    if (w, h) != (expect, expect):
        raise ValueError(
            f"wall graphic must be {expect}x{expect} for tile_px={tile_px}, "
            f"got {w}x{h}; resize deliberately before tiling")
    if flip_horizontal:
        pixels = [[pixels[y][w - 1 - x] for x in range(w)] for y in range(h)]
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tiles = []
    for pos in tile_positions(tile_px):
        tile = [[pixels[pos["y"] + dy][pos["x"] + dx]
                 for dx in range(tile_px)] for dy in range(tile_px)]
        name = f"{pos['node']}.ppm"
        write_ppm(out / name, tile, tile_px, tile_px)
        tiles.append({**pos, "file": name,
                      "sha256": file_sha256(out / name)})
    manifest = {
        "format": "flockinator-tiles/1",
        "generated_utc": utc_iso(time.time()),
        "source": str(image_path),
        "source_sha256": file_sha256(image_path),
        "tile_px": tile_px, "wall_px": expect,
        "flip_horizontal": flip_horizontal,
        "camera_note": "camera sees panels from behind; flip applied "
                       "so content reads correctly from the front",
        "tiles": tiles,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    manifest["manifest"] = str(out / "manifest.json")
    return manifest


def verify_tiles(tiles_dir) -> dict:
    d = Path(tiles_dir)
    manifest = json.loads((d / "manifest.json").read_text())
    for t in manifest["tiles"]:
        p = d / t["file"]
        if not p.exists() or file_sha256(p) != t["sha256"]:
            raise ValueError(f"tile missing or tampered: {t['file']}")
    return {"tiles": len(manifest["tiles"]), "verified": True}
