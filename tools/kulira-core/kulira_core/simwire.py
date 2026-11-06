"""SIM channel v1 reference implementation (host-side, stdlib only).

Implements the contributor-drafted wire spec
(docs/research/contributor-notes/sim-wire-format-v1.md) so firmware
work has an executable reference: 30B common header, HMAC-SHA256
truncated tag, 392B fixed-point world snapshot in 4x98B fragments
with single-slot drop-partial reassembly, INTENT sequencing with
2-tick pipeline and HOLD default, EVENT apply-once tracking.
Simulation channel only; never accepted for management frames.
"""
from __future__ import annotations

import hashlib
import hmac
import struct

MAGIC, VERSION = 0x53, 0x01
SNAP_FRAG, INTENT, EVENT, RESYNC_REQ, RESYNC_REPLY = 1, 2, 3, 4, 5
SENDER_KORVO, SENDER_HOST_TWIN = 0, 0xFE
HDR = struct.Struct("<BBBBI16sIH")
TAG_LEN, MTU = 8, 160
WORLD_BYTES, FRAG_N, FRAG_BYTES = 392, 4, 98
assert HDR.size == 30


def _tag(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha256).digest()[:TAG_LEN]


def fnv1a(data: bytes) -> int:
    h = 0x811C9DC5
    for b in data:
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def pack_frame(key, kind, sender, tick, run_id: bytes, seed, cycle, payload: bytes) -> bytes:
    assert len(run_id) == 16 and len(payload) <= MTU - HDR.size - TAG_LEN
    hdr = HDR.pack(MAGIC, VERSION, kind, sender, tick, run_id, seed, cycle)
    return hdr + payload + _tag(key, hdr + payload)


def unpack_frame(key, frame: bytes):
    """Return (header dict, payload) or None on any validation failure."""
    if len(frame) < HDR.size + TAG_LEN or len(frame) > MTU:
        return None
    hdr, payload, tag = frame[:30], frame[30:-TAG_LEN], frame[-TAG_LEN:]
    if not hmac.compare_digest(tag, _tag(key, hdr + payload)):
        return None
    magic, version, kind, sender, tick, run_id, seed, cycle = HDR.unpack(hdr)
    if magic != MAGIC or version != VERSION:
        return None
    return ({"kind": kind, "sender": sender, "tick": tick,
             "run_id": run_id, "seed": seed, "cycle": cycle}, payload)


def snapshot_frames(key, tick, run_id, seed, cycle, world: bytes, prev_hash: int) -> list[bytes]:
    assert len(world) == WORLD_BYTES
    frames = []
    for idx in range(FRAG_N):
        chunk = world[idx * FRAG_BYTES:(idx + 1) * FRAG_BYTES]
        payload = struct.pack("<BBI", FRAG_N, idx, prev_hash) + chunk
        frames.append(pack_frame(key, SNAP_FRAG, SENDER_KORVO, tick, run_id, seed, cycle, payload))
    return frames


class Reassembler:
    """Single-slot, drop-partial reassembly (spec section 3)."""

    def __init__(self):
        self.tick, self.parts, self.mask, self.prev_hash = None, {}, 0, 0
        self.gaps = 0

    def feed(self, header, payload):
        if header["kind"] not in (SNAP_FRAG, RESYNC_REPLY):
            return None
        total, idx, prev_hash = struct.unpack("<BBI", payload[:6])
        tick = header["tick"]
        if self.tick is not None and tick < self.tick:
            return None  # stale frag, never merged across ticks
        if tick != self.tick:
            if self.tick is not None and self.mask != 0xF:
                self.gaps += 1  # previous tick dropped partial
            self.tick, self.parts, self.mask = tick, {}, 0
            self.prev_hash = prev_hash
        self.parts[idx] = payload[6:6 + FRAG_BYTES]
        self.mask |= 1 << idx
        if self.mask == 0xF:
            world = b"".join(self.parts[i] for i in range(FRAG_N))
            return world if len(world) == WORLD_BYTES else None
        return None


class IntentGate:
    """Per-node intent acceptance: newest seq with base_tick <= T-2."""

    def __init__(self):
        self.last_seq, self.pending = {}, {}

    def offer(self, node, seq, base_tick, cmd: bytes):
        if seq <= self.last_seq.get(node, -1):
            return False  # duplicate / old
        self.last_seq[node] = seq
        self.pending[node] = (base_tick, cmd)
        return True

    def for_tick(self, node, tick):
        got = self.pending.get(node)
        if got and got[0] <= tick - 2:
            return got[1]
        return b"\x00\x00"  # HOLD: vx=vy=0, mode/sensor unchanged


class EventTracker:
    def __init__(self):
        self.applied = set()

    def apply(self, event_id, apply_tick, tick) -> bool:
        if event_id in self.applied or tick < apply_tick:
            return False
        self.applied.add(event_id)
        return True
