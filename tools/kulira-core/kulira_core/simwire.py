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


KINDS = (SNAP_FRAG, INTENT, EVENT, RESYNC_REQ, RESYNC_REPLY)


def pack_frame(key, kind, sender, tick, run_id: bytes, seed, cycle, payload: bytes) -> bytes:
    if len(run_id) != 16 or len(payload) > MTU - HDR.size - TAG_LEN:
        raise ValueError("run_id must be 16B and payload must fit MTU")
    if kind not in KINDS:
        raise ValueError("unknown sim kind")
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
    if magic != MAGIC or version != VERSION or kind not in KINDS:
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
        self.run_id, self.gaps = None, 0  # context tuple once set
        self.completed_tick = -1  # replays at/below this are rejected

    def reset(self, run_id: bytes, seed: int, cycle: int) -> None:
        """Authorized reset for a NEW run (issues #144/#150).

        Only the management layer may call this, after a run has
        been announced on the authenticated management channel.
        It PINS the receiver to the announced (run_id, seed,
        cycle): fragments from any other context are rejected
        before any state mutation, including complete stale
        snapshots from a previous run. Wire traffic alone never
        changes the pin and never clears the replay watermark.
        """
        self.tick, self.parts, self.mask = None, {}, 0
        self.run_id = (run_id, seed, cycle)
        self.completed_tick = -1

    def feed(self, header, payload):
        if header["kind"] not in (SNAP_FRAG, RESYNC_REPLY):
            return None
        if len(payload) != 6 + FRAG_BYTES:
            return None
        total, idx, prev_hash = struct.unpack("<BBI", payload[:6])
        if total != FRAG_N or idx >= FRAG_N:
            return None
        tick = header["tick"]
        if tick <= self.completed_tick:
            return None  # completed or stale snapshot replay: reject
        context = (header["run_id"], header["seed"], header["cycle"])
        if self.run_id is None:
            self.run_id = context  # first-use bootstrap: pin first context
        elif context != self.run_id:
            return None  # foreign context: reject before any mutation
        if self.tick is not None and tick < self.tick:
            return None  # stale frag, never merged across ticks
        if tick != self.tick:
            if self.tick is not None and self.mask != 0xF:
                self.gaps += 1  # previous tick dropped partial
            self.tick, self.parts, self.mask = tick, {}, 0
            self.prev_hash = prev_hash
        elif prev_hash != self.prev_hash:
            return None  # same-tick fork: reject
        self.parts[idx] = payload[6:6 + FRAG_BYTES]
        self.mask |= 1 << idx
        if self.mask == 0xF:
            world = b"".join(self.parts[i] for i in range(FRAG_N))
            self.completed_tick = max(self.completed_tick, tick)
            self.tick, self.parts, self.mask = None, {}, 0  # apply-once
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
            del self.pending[node]  # single-use: never replayed
            if tick - got[0] > 50:
                return b"\x00\x00"  # expired: HOLD
            return got[1]
        return b"\x00\x00"  # HOLD: vx=vy=0, mode/sensor unchanged


class EventTracker:
    WINDOW = 100

    def __init__(self):
        self.applied = set()

    def apply(self, event_id, apply_tick, tick) -> bool:
        if event_id in self.applied:
            return False
        if tick < apply_tick or tick > apply_tick + self.WINDOW:
            return False  # not yet due, or late beyond the apply window
        self.applied.add(event_id)
        return True
