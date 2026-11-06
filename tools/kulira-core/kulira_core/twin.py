"""Host simulation twin: parity comparator for the panel-policy canary.

Deterministic, stdlib-only implementation of the canary decision
rule, producing the exact journal format an ESP32 node will write
to SD. Spec: docs/research/contributor-notes/sim-twin-prototype-spec.md
(supervisor-implemented and tested). Thresholds frozen for canary v1.
"""
from __future__ import annotations

import hashlib
import random

T_HI = 0.70
P_OBS = 0.10
P_LOSS = 0.05
SEARCH, DOUBLE_CHECK, WAIT = 0, 1, 2


def decide(signal: float, obstacle: bool, pkt_loss: bool) -> int:
    if pkt_loss:
        return WAIT
    if obstacle:
        return WAIT
    if signal >= T_HI:
        return DOUBLE_CHECK
    return SEARCH


def input_hash(tick: int, seed: int, signal_q: int, obstacle: bool, loss: bool) -> str:
    h = 0x811C9DC5
    for b in f"{tick}:{seed}:{signal_q}:{int(obstacle)}:{int(loss)}".encode():
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"


def run_twin(seed: int, ticks: int = 500, p_loss: float = P_LOSS,
             p_obs: float = P_OBS) -> list[dict]:
    rng_world = random.Random(seed)
    rng_net = random.Random(seed ^ 0x5BD1E995)
    rows = []
    for tick in range(ticks):
        signal = rng_world.uniform(0.0, 1.0)
        obstacle = rng_world.random() < p_obs
        pkt_loss = rng_net.random() < p_loss
        rows.append({
            "tick": tick, "seed": seed,
            "input_hash": input_hash(tick, seed, int(round(signal * 1000)), obstacle, pkt_loss),
            "decision": decide(signal, obstacle, pkt_loss),
            "latency_us": 0,  # host placeholder; device writes measured micros
        })
    return rows


def to_csv(rows) -> str:
    out = ["tick,seed,input_hash,decision,latency_us"]
    out += [f"{r['tick']},{r['seed']},{r['input_hash']},{r['decision']},{r['latency_us']}"
            for r in rows]
    return "\n".join(out) + "\n"


def parity(host_rows, device_rows) -> dict:
    """Compare host twin vs device journal rows (latency ignored)."""
    n = min(len(host_rows), len(device_rows))
    agree = sum(1 for i in range(n)
                if host_rows[i]["decision"] == device_rows[i]["decision"]
                and host_rows[i]["input_hash"] == device_rows[i]["input_hash"])
    return {"compared": n, "agree": agree,
            "parity": round(agree / n, 4) if n else None,
            "host_rows": len(host_rows), "device_rows": len(device_rows)}
