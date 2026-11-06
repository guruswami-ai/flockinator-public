"""Dataset packager: publishable, replayable mission evidence bundles.

Turns a wall-observer session plus experiment run files into a bundle
others can verify and replay (web page, docker reproduce image):

  dataset/
    dataset.json        manifest: per-file sha256, mission, phases
    redaction.json      what was scanned, stripped, skipped, and why
    frames/             stills (JPEG metadata stripped) + silent video
    telemetry/          journals/scores (allowlisted .json/.jsonl only)

Rules enforced in code, not prose:
  - A video frame entry with publishable != True is skipped, never
    copied (silent-or-not-at-all rule).
  - Telemetry text is scanned for IPv4 addresses, MAC addresses and
    /Users/ paths; any hit fails the build and names the file. The
    bundle must be clean by construction, not by trust.
  - JPEG APPn/COM metadata segments are stripped (GPS EXIF lives
    there); image data after SOS is byte-preserved.
  - Nothing is renamed silently: manifest maps bundle path -> source.

Stdlib only. Wall-session verification reuses wall_observer.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import time
from pathlib import Path

from .wall_observer import file_sha256, utc_iso, verify_session

_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_MAC = re.compile(r"\b(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b")
_USERPATH = re.compile(r"/Users/[^/\s]+/")
TELEMETRY_SUFFIXES = {".json", ".jsonl"}


class DatasetError(RuntimeError):
    pass


def strip_jpeg_metadata(data: bytes) -> bytes:
    """Remove JPEG APPn (0xE0-0xEF) and COM (0xFE) segments.

    Keeps SOI, all coding segments and the entropy data after SOS
    byte-identical. EXIF/GPS/XMP live in APP1, so this removes them.
    """
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        raise DatasetError("not a JPEG (missing SOI)")
    out = bytearray(data[:2])
    i = 2
    while i + 4 <= len(data):
        if data[i] != 0xFF:
            raise DatasetError(f"JPEG marker expected at {i}")
        marker = data[i + 1]
        if marker == 0xDA:  # SOS: rest is entropy data, copy verbatim
            out += data[i:]
            return bytes(out)
        length = int.from_bytes(data[i + 2:i + 4], "big")
        if length < 2 or i + 2 + length > len(data):
            raise DatasetError("truncated JPEG segment")
        if 0xE0 <= marker <= 0xEF or marker == 0xFE:
            pass  # strip metadata segment
        else:
            out += data[i:i + 2 + length]
        i += 2 + length
    raise DatasetError("JPEG ended before SOS")


def scan_text(text: str) -> list[str]:
    findings = []
    for name, rx in (("ipv4", _IPV4), ("mac", _MAC), ("user_path", _USERPATH)):
        for m in rx.finditer(text):
            findings.append(f"{name}:{m.group(0)[:32]}")
    return findings


def build_dataset(session_dir, telemetry_dir, out_dir, mission_id: str,
                  entry_point: str = "cli") -> dict:
    session, out = Path(session_dir), Path(out_dir)
    verify_session(session)  # hash chain + frame hashes, or raise
    entries = [json.loads(line) for line in
               (session / "manifest.jsonl").read_text().splitlines() if line.strip()]
    out.mkdir(parents=True, exist_ok=True)
    (out / "frames").mkdir(exist_ok=True)
    files, skipped = [], []

    for e in entries:
        if e.get("kind") != "frame":
            continue
        p = e["payload"]
        src = session / p["file"]
        if p.get("kind_media") == "video" and not p.get("publishable"):
            skipped.append({"file": p["file"],
                            "reason": "video not silent (publishable=false)"})
            continue
        dest_name = f"{p['seq']:04d}_{src.name}"
        dest = out / "frames" / dest_name
        if src.suffix.lower() in (".jpg", ".jpeg"):
            dest.write_bytes(strip_jpeg_metadata(src.read_bytes()))
            stripped = dest.stat().st_size != src.stat().st_size
        else:
            shutil.copyfile(src, dest)
            stripped = bool(p.get("audio_stripped"))
        files.append({"path": f"frames/{dest_name}", "source": p["file"],
                      "sha256": file_sha256(dest), "bytes": dest.stat().st_size,
                      "phase": p.get("phase"), "kind_media": p.get("kind_media"),
                      "metadata_stripped": stripped})

    telemetry_copied = []
    if telemetry_dir:
        tdir = Path(telemetry_dir)
        (out / "telemetry").mkdir(exist_ok=True)
        for src in sorted(tdir.rglob("*")):
            if not src.is_file() or src.suffix.lower() not in TELEMETRY_SUFFIXES:
                continue
            text = src.read_text(errors="strict")
            hits = scan_text(text)
            if hits:
                raise DatasetError(
                    f"redaction scan failed for {src}: {hits[:5]}; "
                    "refusing to bundle unredacted telemetry")
            rel = src.relative_to(tdir)
            dest = out / "telemetry" / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
            telemetry_copied.append(str(rel))

    manifest = {
        "mission_id": mission_id, "entry_point": entry_point,
        "generated_utc": utc_iso(time.time()),
        "source_session": session.name,
        "files": files, "telemetry": telemetry_copied,
        "skipped": skipped,
        "rules": ["silent-video-only", "jpeg-metadata-stripped",
                  "telemetry scanned: ipv4/mac/user-paths fail the build",
                  "simulated SIM states only; no device identities"],
    }
    (out / "dataset.json").write_text(json.dumps(manifest, indent=1))
    (out / "redaction.json").write_text(json.dumps(
        {"scanned_telemetry_files": len(telemetry_copied),
         "skipped": skipped,
         "jpeg_metadata_stripped_files": sum(
             1 for f in files if f["metadata_stripped"])}, indent=1))
    manifest["dataset_json"] = str(out / "dataset.json")
    return manifest


def verify_dataset(dataset_dir) -> dict:
    d = Path(dataset_dir)
    manifest = json.loads((d / "dataset.json").read_text())
    for f in manifest["files"]:
        p = d / f["path"]
        if not p.exists() or file_sha256(p) != f["sha256"]:
            raise DatasetError(f"dataset file missing or tampered: {f['path']}")
    return {"files": len(manifest["files"]),
            "telemetry": len(manifest["telemetry"]),
            "skipped": len(manifest["skipped"]), "verified": True}
