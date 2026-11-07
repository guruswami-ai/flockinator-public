"""End-to-end host prototype loop: world core + twin rule + wire.

One robot is driven by the canary decision rule toward a survivor:
signal is proximity-quantized; SEARCH steers toward the survivor,
DOUBLE_CHECK/WAIT hold. Every tick produces a simwire snapshot
frame set and a twin-format journal row. Deterministic; this is
the host rehearsal of the panel-policy canary, not node evidence.
"""
from __future__ import annotations

from .simcore import World
from .simwire import snapshot_frames, fnv1a
from .twin import SEARCH, DOUBLE_CHECK, WAIT, decide, input_hash, missing_hash


def run_loop(seed: int, ticks: int = 300, key: bytes = b"k" * 32,
             run_id: bytes = bytes(range(16)),
             drop_ticks: frozenset = frozenset()) -> dict:
    """drop_ticks: ticks where the robot receives no input at all.

    Those ticks journal a missing-input row (contract v1.1) with
    decision WAIT and no motion - the host rehearsal of canary
    loss behaviour.
    """
    world = World(seed)
    sx, sy = world.survivor
    journal, frames = [], 0
    found_tick = None
    prev_hash = 0
    for tick in range(ticks):
        if tick in drop_ticks:
            world.step({})
            journal.append({"tick": tick, "seed": seed,
                            "input_hash": missing_hash(tick, seed),
                            "decision": WAIT, "latency_us": 0})
            continue
        r = world.robots[0]
        dist = max(abs(sx - r["x"]), abs(sy - r["y"]))  # Chebyshev, dm
        signal_q = max(0, 1000 - dist // 4)
        decision = decide(min(signal_q, 1000), obstacle=False, pkt_loss=False)
        intent = {}
        if decision in (SEARCH, DOUBLE_CHECK):
            # SEARCH: full approach. DOUBLE_CHECK: slow final approach
            # to verify (holding still would never confirm a contact).
            sp = 300 if decision == SEARCH else 100
            vx = sp if sx > r["x"] else -sp if sx < r["x"] else 0
            vy = sp if sy > r["y"] else -sp if sy < r["y"] else 0
            intent = {0: (vx, vy)}
        world.step(intent)
        snap = world.snapshot(reveal_survivor=False)
        frames += len(snapshot_frames(key, world.tick, run_id, seed, 1, snap, prev_hash))
        prev_hash = fnv1a(snap)
        journal.append({"tick": tick, "seed": seed,
                        "input_hash": input_hash(tick, seed, min(signal_q, 1000), False, False),
                        "decision": decision, "latency_us": 0})
        if dist <= 30 and found_tick is None:
            found_tick = tick
            break
    return {"found_tick": found_tick, "journal": journal, "frames": frames,
            "ticks_run": len(journal)}
