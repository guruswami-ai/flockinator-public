"""Mission slate: a checksum frame for the start/end of a sequence.

If a video or frame set is separated from its manifest, the slate is
what still identifies it. It carries, in human-readable text and in
one machine-readable QR payload:

  mission id - UTC date - short mission checksum - telemetry hash

The checksum is derived, never invented:
  sha256(mission_id | started_utc | telemetry_sha256 | frame_hashes)
so any bundle can recompute it and prove the slate belongs to the
data. The QR payload is the same fields as compact JSON (<200 chars,
low QR version, decodable at wall-capture distance).

Panel-side counterpart (spec for the firmware owner, not implemented
here): at mission start and end the wall itself should hold a slate
for >=3 s - mission text across the top tiles and ONE large QR
spanning all 16 tiles. Each tile is 64x64 panel pixels, so the wall
is a 256x256 canvas: a version-8 QR (49x49 modules) gives ~5 panel
pixels per module and ~20 camera pixels per module in a 1080-wide
capture - comfortably decodable. Per-tile QRs are NOT viable at
64x64 (a version-3 code already wants 29 modules before quiet
zones); per-tile data belongs in text (firmware version line), not
in a code.

Pillow renders the PNG (optional 'report'/'slate' dependency);
segno supplies the QR matrix when installed. Both are injected in
tests. Without them the text slate data is still generated and the
manifest records qr/image as absent rather than faking them.
"""
from __future__ import annotations

import hashlib
import json


SLATE_FORMAT = "flockinator-slate/1"
_CHECKSUM_RE = __import__("re").compile(r"^FLOCK-[0-9A-F]{16}$")


def validate_qr_payload(text: str) -> dict:
    """Boundary validation for a scanned slate payload.

    Slate format v1 (additive-only: new fields may appear, v1 fields
    never change meaning): {v:1, mission:str, utc:str, ck:FLOCK-HEX16,
    telemetry_sha256?:hex-prefix}. Anything else is rejected, so a
    decoder never has to guess which format it is looking at.
    """
    try:
        d = json.loads(text)
    except Exception as e:
        raise ValueError(f"slate payload is not JSON: {e}") from e
    if not isinstance(d, dict) or d.get("v") != 1:
        raise ValueError("unsupported slate version (expected v=1)")
    if not isinstance(d.get("mission"), str) or not d["mission"]:
        raise ValueError("slate mission missing")
    if not isinstance(d.get("utc"), str) or not d["utc"]:
        raise ValueError("slate utc missing")
    if not _CHECKSUM_RE.match(str(d.get("ck", ""))):
        raise ValueError("slate checksum malformed (FLOCK-<16 hex>)")
    return d


def mission_checksum(mission_id: str, started_utc: str,
                     telemetry_sha256: str = "",
                     frame_sha256s: list[str] | None = None) -> str:
    h = hashlib.sha256()
    h.update(f"{mission_id}|{started_utc}|{telemetry_sha256}".encode())
    for f in sorted(frame_sha256s or []):
        h.update(f.encode())
    return "FLOCK-" + h.hexdigest()[:16].upper()


def qr_payload(mission_id: str, started_utc: str, checksum: str,
               telemetry_sha256: str = "") -> str:
    payload = {"v": 1, "mission": mission_id, "utc": started_utc,
               "ck": checksum}
    if telemetry_sha256:
        payload["telemetry_sha256"] = telemetry_sha256[:16]
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def segno_matrix(payload: str):
    """QR module matrix via segno, or None when segno is absent."""
    try:
        import segno
    except ImportError:
        return None
    qr = segno.make(payload, error="m")
    return [[bool(v) for v in row] for row in qr.matrix]


def render_slate_png(path, mission_id: str, started_utc: str,
                     checksum: str, payload: str, matrix=None,
                     size: int = 960) -> bool:
    """Render the slate PNG. Returns False when Pillow is absent."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return False
    img = Image.new("RGB", (size, size), (14, 18, 22))
    dr = ImageDraw.Draw(img)
    big = ImageFont.load_default(size=44)
    mid = ImageFont.load_default(size=30)
    small = ImageFont.load_default(size=24)
    dr.text((36, 30), "FLOCKINATOR MISSION SLATE", fill=(235, 240, 244), font=big)
    dr.text((36, 92), f"MISSION  {mission_id}", fill=(235, 240, 244), font=big)
    dr.text((36, 148), f"UTC  {started_utc}", fill=(190, 200, 208), font=mid)
    dr.text((36, 190), f"CHECKSUM  {checksum}", fill=(190, 200, 208), font=mid)
    if matrix:
        n = len(matrix)
        box = 520
        cell = box // n
        ox, oy = (size - cell * n) // 2, 260
        dr.rectangle([ox - 16, oy - 16, ox + cell * n + 16, oy + cell * n + 16],
                     fill=(255, 255, 255))
        for y, row in enumerate(matrix):
            for x, v in enumerate(row):
                if v:
                    dr.rectangle([ox + x * cell, oy + y * cell,
                                  ox + (x + 1) * cell, oy + (y + 1) * cell],
                                 fill=(10, 10, 10))
        dr.text((36, oy + cell * n + 36),
                "Scan: mission, UTC, checksum, telemetry hash",
                fill=(190, 200, 208), font=small)
    else:
        dr.text((36, 300), "QR unavailable (install segno); checksum above is authoritative",
                fill=(220, 180, 120), font=small)
    dr.text((36, size - 60), "Simulated mission data. No live nodes. Verify: kulira dataset verify",
            fill=(150, 160, 168), font=small)
    img.save(path)
    return True
