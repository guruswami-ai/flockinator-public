"""Wall observer: timestamped camera capture of the 16-panel wall.

Captures stills (burst-capable) and video from the USB-attached phone
facing the Flockinator panels, and writes a hash-chained manifest
(reusing kulira_core.log.AttackLog) that ties every frame to a mission
phase (beginning / training / end) and to UTC + host-monotonic time.

Questions this instrumentation answers:
  1. What did the wall visually show at mission time T?
  2. Can a published frame be trusted (sha256 + hash chain intact)?
  3. How far apart were phone and host clocks when the frame was taken?

Publishable by construction: no raw device serial, MAC, or lab-network
data is recorded. The phone is identified only by model + a sha256 of
its adb serial. Panel frames show simulated SIM states only.

Camera notes (measured 2026-11-06, Pixel 9a / GrapheneOS Camera):
  - CAMERA (auto) mode renders the multiplexed panels correctly.
  - NIGHT mode produces thick black bands (stacking beats against the
    panel scanout). Never use NIGHT for the wall.
  - If flicker appears in dynamic states, average a burst of auto
    frames; 3 frames cut measured banding ~3.5x.

Host-side only, stdlib only. ADB is driven through an injectable
runner so tests need no phone.
"""
from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from .log import AttackLog

CAMERA_INTENT = "android.media.action.STILL_IMAGE_CAMERA"
DCIM = "/sdcard/DCIM/Camera"

# GrapheneOS Camera mode-tab centres at 1080x2424 (from uiautomator
# dump 2026-11-06). Fallback coordinates.
MODE_TABS = {"CAMERA": (540, 2147), "NIGHT": (303, 2147),
             "VIDEO": (775, 2147), "QR SCAN": (80, 2147)}
FORBIDDEN_MODES = {"NIGHT"}  # banding: stacking vs panel scanout


def utc_iso(epoch_s: float) -> str:
    return datetime.fromtimestamp(epoch_s, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def device_tag(serial: str) -> str:
    """Opaque publishable device identifier (never the raw serial)."""
    return "sha256:" + hashlib.sha256(serial.encode()).hexdigest()[:16]


def file_sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class AdbError(RuntimeError):
    pass


def strip_audio_inplace(path) -> bool:
    """Remove audio tracks with ffmpeg (publishable-video rule).

    Household/lab audio must never ship with wall video. Lossless
    video remux; returns False when ffmpeg is unavailable, so the
    caller can record the video as NOT publishable.
    """
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False
    tmp = str(path) + ".silent.mp4"
    r = subprocess.run([ffmpeg, "-y", "-v", "error", "-i", str(path),
                        "-map", "0:v:0", "-c:v", "copy", "-an", tmp],
                       capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise AdbError(f"ffmpeg audio strip failed: {r.stderr.strip()[:200]}")
    Path(tmp).replace(path)
    return True


class Adb:
    """Thin adb wrapper; `runner` injectable for tests."""

    def __init__(self, adb_path: str = "adb", serial: str | None = None,
                 runner=subprocess.run):
        self.adb_path = adb_path
        self.serial = serial
        self.runner = runner

    def _cmd(self, *args: str) -> str:
        cmd = [self.adb_path]
        if self.serial:
            cmd += ["-s", self.serial]
        cmd += list(args)
        r = self.runner(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            raise AdbError(f"adb {' '.join(args[:2])} failed: {r.stderr.strip()}")
        return r.stdout.strip()

    def shell(self, *args: str) -> str:
        return self._cmd("shell", *args)

    def pull(self, remote: str, local) -> None:
        self._cmd("pull", remote, str(local))

    def phone_epoch(self) -> float:
        return float(self.shell("date", "+%s"))

    def model(self) -> str:
        return self.shell("getprop", "ro.product.model")

    def dcim_listing(self) -> set[str]:
        out = self.shell("ls", DCIM)
        return set(out.split()) if out else set()


class WallSession:
    """One mission-observation session: frames + hash-chained manifest."""

    def __init__(self, out_dir, mission_id: str, adb: Adb,
                 entry_point: str = "cli"):
        self.dir = Path(out_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "frames").mkdir(exist_ok=True)
        self.mission_id = mission_id
        self.adb = adb
        self.seq = 0
        self.log = AttackLog(self.dir / "manifest.jsonl",
                             clock=lambda: utc_iso(time.time()))
        host = time.time()
        try:
            phone = adb.phone_epoch()
            offset = round(phone - host, 3)
            model = adb.model()
        except Exception as e:  # phone facts are provenance, not a gate
            phone, offset, model = None, None, f"unavailable: {e}"
        self.start = self.log.append("session_start", {
            "mission_id": mission_id,
            "entry_point": entry_point,
            "host_utc": utc_iso(host),
            "host_epoch_s": round(host, 3),
            "host_monotonic_s": round(time.monotonic(), 3),
            "phone_model": model,
            "phone_utc": utc_iso(phone) if phone is not None else None,
            "phone_minus_host_clock_s": offset,
            "device": device_tag(adb.serial) if adb.serial else None,
            "camera_mode_required": "CAMERA (auto); NIGHT forbidden (banding)",
            "execution": "wall_observation_only",
        })

    def mark(self, phase: str, note: str = "") -> dict:
        """Stamp a mission-phase transition (beginning/training/end/...)."""
        return self.log.append("phase_marker", {
            "mission_id": self.mission_id, "phase": phase, "note": note,
            "host_utc": utc_iso(time.time()),
            "host_monotonic_s": round(time.monotonic(), 3),
        })

    def _wait_new_file(self, before: set[str], suffix: str,
                       timeout_s: float = 30.0) -> str:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            now = self.adb.dcim_listing()
            new = sorted(f for f in now - before if f.endswith(suffix))
            if new:
                return new[-1]
            time.sleep(0.5)
        raise AdbError(f"no new {suffix} file in {DCIM} within {timeout_s}s")

    def capture_still(self, phase: str, burst: int = 1,
                      burst_gap_s: float = 1.0) -> list[dict]:
        """Capture `burst` stills; returns manifest entries (kind=frame)."""
        entries = []
        for _ in range(burst):
            before = self.adb.dcim_listing()
            t0 = time.time()
            self.adb.shell("input", "keyevent", "27")
            name = self._wait_new_file(before, ".jpg")
            self.seq += 1
            local = self.dir / "frames" / f"f{self.seq:04d}_{name}"
            self.adb.pull(f"{DCIM}/{name}", local)
            entries.append(self.log.append("frame", {
                "mission_id": self.mission_id, "phase": phase,
                "seq": self.seq, "kind_media": "still",
                "file": f"frames/{local.name}",
                "phone_file": name,
                "sha256": file_sha256(local),
                "bytes": local.stat().st_size,
                "host_utc_requested": utc_iso(t0),
                "host_utc_pulled": utc_iso(time.time()),
                "host_monotonic_s": round(time.monotonic(), 3),
                "camera_mode": "CAMERA",
            }))
            if burst_gap_s:
                time.sleep(burst_gap_s)
        return entries

    def capture_video(self, phase: str, seconds: float,
                      shutter_xy=(539, 1917),
                      strip_audio: bool = True) -> dict:
        """Record `seconds` of VIDEO-mode video, restore CAMERA mode.

        The stored file has its audio track stripped (ffmpeg) when
        ffmpeg is available; the manifest records whether that
        happened. A video with audio_stripped=False is NOT
        publishable. Note VIDEO mode frames 16:9 and crops the wall
        vertically; use still bursts (identical FOV to the wall
        report) when the full 4x4 must be in frame.
        """
        self.tap_mode("VIDEO")
        time.sleep(2)
        before = self.adb.dcim_listing()
        t0 = time.time()
        self.adb.shell("input", "tap", str(shutter_xy[0]), str(shutter_xy[1]))
        time.sleep(seconds)
        self.adb.shell("input", "tap", str(shutter_xy[0]), str(shutter_xy[1]))
        time.sleep(3)
        self.tap_mode("CAMERA")
        name = self._wait_new_file(before, ".mp4", timeout_s=60.0)
        self.seq += 1
        local = self.dir / "frames" / f"f{self.seq:04d}_{name}"
        self.adb.pull(f"{DCIM}/{name}", local)
        original_sha = file_sha256(local)
        stripped = strip_audio_inplace(local) if strip_audio else False
        return self.log.append("frame", {
            "mission_id": self.mission_id, "phase": phase,
            "seq": self.seq, "kind_media": "video",
            "file": f"frames/{local.name}", "phone_file": name,
            "sha256": file_sha256(local), "bytes": local.stat().st_size,
            "original_sha256": original_sha,
            "audio_stripped": stripped,
            "publishable": bool(stripped),
            "duration_s_requested": seconds,
            "host_utc_requested": utc_iso(t0),
            "host_utc_pulled": utc_iso(time.time()),
            "host_monotonic_s": round(time.monotonic(), 3),
            "camera_mode": "VIDEO",
            "fov_note": "16:9 crop; full wall via still bursts",
        })

    def tap_mode(self, mode: str) -> None:
        """Tap a camera mode tab found in the UI dump (tab positions
        shift with the active mode, so constants alone are unsafe)."""
        x = y = None
        try:
            self.adb.shell("uiautomator", "dump", "/sdcard/_wall_ui.xml")
            xml = self.adb.shell("cat", "/sdcard/_wall_ui.xml")
            m = re.search(r'text="%s"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
                          % re.escape(mode), xml)
            if m:
                a, b, c, d = (int(v) for v in m.groups())
                x, y = (a + c) // 2, (b + d) // 2
        except Exception:
            x = y = None
        if x is None:
            x, y = MODE_TABS[mode]
        self.adb.shell("input", "tap", str(x), str(y))

    def open_camera(self, mode: str = "CAMERA") -> None:
        if mode in FORBIDDEN_MODES:
            raise AdbError(f"{mode} mode forbidden for panels (banding)")
        self.adb.shell("am", "start", "-a", CAMERA_INTENT)
        time.sleep(3)
        if mode != "CAMERA":
            self.tap_mode(mode)
            time.sleep(2)

    def close(self, note: str = "") -> dict:
        host = time.time()
        try:
            drift = round(self.adb.phone_epoch() - host, 3)
        except Exception:
            drift = None
        return self.log.append("session_end", {
            "mission_id": self.mission_id, "note": note,
            "host_utc": utc_iso(host),
            "phone_minus_host_clock_s": drift,
            "frames": self.seq,
        })


def verify_session(session_dir) -> dict:
    """Verify hash chain + every frame file's sha256."""
    from .log import verify_log
    d = Path(session_dir)
    entries = verify_log(d / "manifest.jsonl")
    frames = 0
    for e in entries:
        if e["kind"] == "frame":
            p = d / e["payload"]["file"]
            if not p.exists():
                raise AdbError(f"missing frame file {p}")
            if file_sha256(p) != e["payload"]["sha256"]:
                raise AdbError(f"sha256 mismatch {p}")
            frames += 1
    return {"entries": len(entries), "frames": frames,
            "log_verified": True}
