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
import subprocess
import time
from pathlib import Path

from .wall_observer import file_sha256, utc_iso, verify_session

# Publication derivatives: verification media only needs timeline
# legibility and synchronisation with the manifest timestamps, not
# full sensor resolution. Originals stay in frames/ untouched.
WEB_VIDEO_WIDTH = 854
WEB_STILL_WIDTH = 1280

_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_IPV6_FULL = re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){4,7}[0-9a-fA-F]{1,4}\b")
_IPV6_COMPRESSED = re.compile(r"\b[0-9a-fA-F]{0,4}(?::[0-9a-fA-F]{0,4})*::[0-9a-fA-F:]+\b")
_MAC = re.compile(r"\b(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b")
_MAC_DASH = re.compile(r"\b(?:[0-9a-fA-F]{2}-){5}[0-9a-fA-F]{2}\b")
_MAC_DOT = re.compile(r"\b(?:[0-9a-fA-F]{4}\.){2}[0-9a-fA-F]{4}\b")
_USERPATH = re.compile(r"(?:/Users/|/home/|C:\\Users\\)[^\s/\\]+")
_LOCALHOSTNAME = re.compile(r"\b[a-zA-Z0-9-]+\.local\b")
TELEMETRY_SUFFIXES = {".json", ".jsonl"}
_SCANNERS = (("ipv4", _IPV4), ("ipv6", _IPV6_FULL), ("ipv6", _IPV6_COMPRESSED),
             ("mac", _MAC), ("mac", _MAC_DASH), ("mac", _MAC_DOT),
             ("user_path", _USERPATH), ("local_hostname", _LOCALHOSTNAME))


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
        if marker == 0xFF:  # padding fill byte before a marker
            i += 1
            continue
        if marker == 0x01 or 0xD0 <= marker <= 0xD9:
            out += data[i:i + 2]  # standalone marker, no length field
            i += 2
            continue
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


_PNG_DROP = {b"tEXt", b"zTXt", b"iTXt", b"eXIf"}


def strip_png_metadata(data: bytes) -> bytes:
    """Drop PNG text/EXIF chunks (tEXt/zTXt/iTXt/eXIf); keep the rest."""
    sig = b"\x89PNG\r\n\x1a\n"
    if not data.startswith(sig):
        raise DatasetError("not a PNG (missing signature)")
    out = bytearray(sig)
    i = len(sig)
    while i + 8 <= len(data):
        length = int.from_bytes(data[i:i + 4], "big")
        ctype = data[i + 4:i + 8]
        end = i + 8 + length + 4
        if end > len(data):
            raise DatasetError("truncated PNG chunk")
        if ctype not in _PNG_DROP:
            out += data[i:end]
        i = end
        if ctype == b"IEND":
            return bytes(out)
    raise DatasetError("PNG ended before IEND")


def scan_text(text: str) -> list[str]:
    findings = []
    for name, rx in _SCANNERS:
        for m in rx.finditer(text):
            findings.append(f"{name}:{m.group(0)[:32]}")
    return findings


def _derivative(src: Path, dest: Path, width: int, is_video: bool):
    """Downscale one media file with ffmpeg; None if unavailable/failed."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [ffmpeg, "-y", "-v", "error", "-i", str(src)]
    if is_video:
        cmd += ["-vf", f"scale={width}:-2", "-c:v", "libx264",
                "-crf", "28", "-preset", "veryfast", "-an"]
    else:
        cmd += ["-vf", f"scale={width}:-2", "-q:v", "4"]
    cmd.append(str(dest))
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
    if r.returncode != 0 or not dest.exists():
        return None
    return dest


def build_dataset(session_dir, telemetry_dir, out_dir, mission_id: str,
                  entry_point: str = "cli", derivatives: bool = True) -> dict:
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
        src = (session / p["file"]).resolve()
        if not src.is_relative_to(session.resolve()) or src.is_symlink():
            raise DatasetError(f"frame path escapes session: {p['file']}")
        if p.get("kind_media") == "video" and p.get("publishable") is not True:
            skipped.append({"file": p["file"],
                            "reason": "video not silent (publishable=false)"})
            continue
        dest_name = f"{p['seq']:04d}_{src.name}"
        dest = out / "frames" / dest_name
        if dest.exists():
            raise DatasetError(f"duplicate frame destination: {dest_name}")
        if src.suffix.lower() in (".jpg", ".jpeg"):
            dest.write_bytes(strip_jpeg_metadata(src.read_bytes()))
            stripped = dest.stat().st_size != src.stat().st_size
        elif src.suffix.lower() == ".png":
            raw = src.read_bytes()
            dest.write_bytes(strip_png_metadata(raw))
            stripped = dest.stat().st_size != len(raw)
        else:
            shutil.copyfile(src, dest)
            stripped = bool(p.get("audio_stripped"))
        entry = {"path": f"frames/{dest_name}", "source": p["file"],
                 "sha256": file_sha256(dest), "bytes": dest.stat().st_size,
                 "phase": p.get("phase"), "kind_media": p.get("kind_media"),
                 "metadata_stripped": stripped}
        if derivatives:
            is_vid = p.get("kind_media") == "video"
            web = out / "web" / (dest.stem + ".web" +
                                 (".mp4" if is_vid else ".jpg"))
            made = _derivative(dest, web,
                               WEB_VIDEO_WIDTH if is_vid else WEB_STILL_WIDTH,
                               is_vid)
            if made is not None:
                entry["web_derivative"] = {
                    "path": f"web/{web.name}", "sha256": file_sha256(web),
                    "bytes": web.stat().st_size,
                    "sync_note": "same seq/phase and manifest timestamps "
                                 "as the original; resolution reduced "
                                 "for publication only"}
            else:
                entry["web_derivative"] = None
        files.append(entry)

    telemetry_copied = []
    if telemetry_dir:
        tdir = Path(telemetry_dir)
        (out / "telemetry").mkdir(exist_ok=True)
        for src in sorted(tdir.rglob("*")):
            if src.is_symlink():
                raise DatasetError(f"telemetry symlink refused: {src}")
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

    # Mission slate: checksum frame identifying this bundle even if
    # separated from dataset.json (see kulira_core.slate, format v1).
    from .slate import (mission_checksum, qr_payload, render_slate_png,
                        segno_matrix)
    started = next((e["payload"].get("host_utc") for e in entries
                    if e.get("kind") == "session_start"), "")
    tel_hash = ""
    if telemetry_copied:
        hh = hashlib.sha256()
        for rel in telemetry_copied:
            hh.update(file_sha256(out / "telemetry" / rel).encode())
        tel_hash = hh.hexdigest()
    checksum = mission_checksum(
        mission_id, started or "", tel_hash,
        [f["sha256"] for f in files])
    payload = qr_payload(mission_id, started or "", checksum, tel_hash)
    slate_info = {"format": "flockinator-slate/1", "checksum": checksum,
                  "started_utc": started, "qr_payload": payload,
                  "image": None, "video_clips": []}
    (out / "web").mkdir(exist_ok=True)
    slate_png = out / "web" / "slate.png"
    if render_slate_png(slate_png, mission_id, started or "", checksum,
                        payload, matrix=segno_matrix(payload)):
        slate_info["image"] = "web/slate.png"
        for name in ("slate-start.mp4", "slate-end.mp4"):
            dest = out / "web" / name
            if _derivative(slate_png, dest, WEB_VIDEO_WIDTH, True) is not None:
                slate_info["video_clips"].append(f"web/{name}")

    manifest = {
        "mission_id": mission_id, "entry_point": entry_point,
        "slate": slate_info,
        "generated_utc": utc_iso(time.time()),
        "source_session": session.name,
        "files": files, "telemetry": telemetry_copied,
        "skipped": skipped,
        "rules": ["silent-video-only", "jpeg-metadata-stripped",
                  "telemetry scanned: ip/mac/hostname/user-paths fail the build",
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
        web = f.get("web_derivative")
        if web:
            wp = d / web["path"]
            if not wp.exists() or file_sha256(wp) != web["sha256"]:
                raise DatasetError(
                    f"web derivative missing or tampered: {web['path']}")
    return {"files": len(manifest["files"]),
            "telemetry": len(manifest["telemetry"]),
            "skipped": len(manifest["skipped"]), "verified": True}
