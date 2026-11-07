"""Deterministic shared-world simulation core (host prototype).

Integer-only kinematics in decimetres at a logical 10 ticks/sec,
producing the 392B fixed-point snapshot consumed by simwire:
8B header (tick u32, survivor x/y i16, 0x7FFF = hidden) + 16 x 24B
robot records. Stdlib only, no wall clock, no floats in state.
Firmware port target: same integer equations on Korvo + panels.
"""
from __future__ import annotations

import math
import struct

ROBOTS = 16
HDR = struct.Struct("<Ihh")
REC = struct.Struct("<hhHhBBBBhhII")
assert HDR.size == 8 and REC.size == 24
HIDDEN = 0x7FFF
MAX_SPEED = 300  # cm/s clamp


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def _tdiv(a: int, b: int) -> int:
    """Truncating division (C semantics), NOT Python floor division.

    vx=-15: C gives -1, Python // gives -2. The C port is the
    reference semantics; this helper keeps both identical.
    """
    q = abs(a) // abs(b)
    return q if (a < 0) == (b < 0) else -q


class World:
    def __init__(self, seed: int, survivor=(2400, 2400)):
        self.tick = 0
        self.seed = seed
        self.survivor = survivor  # dm, or None (hidden in snapshot)
        # deterministic grid start: 4x4 at 200dm spacing from (200,200)
        self.robots = [{"x": 200 + (i % 4) * 200, "y": 200 + (i // 4) * 200,
                        "heading": 0, "speed": 0, "mode": 0, "flags": 1,
                        "ack_seq": 0, "rssi": 0, "tx": 0, "ty": 0,
                        "sensor": 0} for i in range(ROBOTS)]

    def step(self, intents: dict) -> None:
        """intents: node id -> (vx, vy) in cm/s. Missing = HOLD (0,0)."""
        for i, r in enumerate(self.robots):
            vx, vy = intents.get(i, (0, 0))
            vx, vy = _clamp(vx, -MAX_SPEED, MAX_SPEED), _clamp(vy, -MAX_SPEED, MAX_SPEED)
            r["x"] = _clamp(r["x"] + _tdiv(vx, 10), -32000, 32000)
            r["y"] = _clamp(r["y"] + _tdiv(vy, 10), -32000, 32000)
            r["speed"] = math.isqrt(vx * vx + vy * vy) if (vx or vy) else 0
            if vx or vy:
                # heading in decidegrees, integer atan2-free quadrant approx
                r["heading"] = (r["heading"] + (5 if vy > 0 else -5 if vy < 0 else 0)) % 3600
        self.tick += 1

    def snapshot(self, reveal_survivor: bool = False) -> bytes:
        sx, sy = self.survivor if (reveal_survivor and self.survivor) else (HIDDEN, HIDDEN)
        out = [HDR.pack(self.tick, sx, sy)]
        for r in self.robots:
            out.append(REC.pack(r["x"], r["y"], r["heading"], r["speed"],
                                r["mode"], r["flags"], r["ack_seq"], r["rssi"],
                                r["tx"], r["ty"], r["sensor"], 0))
        return b"".join(out)

    @staticmethod
    def decode(data: bytes) -> dict:
        if len(data) != 8 + ROBOTS * 24:
            raise ValueError(f"snapshot must be 392 bytes, got {len(data)}")
        tick, sx, sy = HDR.unpack(data[:8])
        robots = []
        for i in range(ROBOTS):
            v = REC.unpack(data[8 + i * 24:8 + (i + 1) * 24])
            robots.append({"x": v[0], "y": v[1], "heading": v[2], "speed": v[3],
                           "mode": v[4], "flags": v[5], "ack_seq": v[6],
                           "rssi": v[7], "tx": v[8], "ty": v[9], "sensor": v[10]})
        return {"tick": tick, "survivor": (sx, sy), "robots": robots}
