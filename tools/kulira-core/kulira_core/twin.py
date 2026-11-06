"""Host simulation twin: parity comparator for the panel-policy canary.

Deterministic, stdlib-only implementation of the canary decision
rule, producing the exact journal format an ESP32 node will write
to SD. Spec: docs/research/contributor-notes/sim-twin-prototype-spec.md
(supervisor-implemented and tested). Thresholds frozen for canary v1.
"""
from __future__ import annotations

import random

T_HI = 0.70
P_OBS = 0.10
P_LOSS = 0.05
SEARCH, DOUBLE_CHECK, WAIT = 0, 1, 2


def decide(signal_q: int, obstacle: bool, pkt_loss: bool) -> int:
    """Decision on quantized signal (integer compare, C-portable)."""
    if pkt_loss:
        return WAIT
    if obstacle:
        return WAIT
    if signal_q >= 700:
        return DOUBLE_CHECK
    return SEARCH


def expected_distribution(p_loss: float, p_obs: float = P_OBS) -> dict:
    """Analytic decision distribution (contributor-derived, wave 5)."""
    wait = p_loss + (1 - p_loss) * p_obs
    double = (1 - p_loss) * (1 - p_obs) * (1 - T_HI)
    return {"WAIT": round(wait, 4), "DOUBLE_CHECK": round(double, 4),
            "SEARCH": round(1 - wait - double, 4)}


def input_hash(tick: int, seed: int, signal_q: int, obstacle: bool, loss: bool) -> str:
    h = 0x811C9DC5
    for b in f"{tick}:{seed}:{signal_q}:{int(obstacle)}:{int(loss)}".encode():
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"


def run_twin(seed: int, ticks: int = 500, p_loss: float = P_LOSS,
             p_obs: float = P_OBS) -> list[dict]:
    # Three independent streams (signal / obstacle / loss). NOTE: input
    # generation is host-side simulation of the broadcast input stream;
    # the device decides on inputs it receives, never on its own RNG.
    rng_sig = random.Random(seed)
    rng_obs = random.Random(seed ^ 0x5BD1E995)
    rng_net = random.Random(seed ^ 0x27D4EB2D)
    rows = []
    for tick in range(ticks):
        # half-up quantization (matches C round(), not Python banker's)
        signal_q = int(rng_sig.uniform(0.0, 1.0) * 1000 + 0.5)
        obstacle = rng_obs.random() < p_obs
        pkt_loss = rng_net.random() < p_loss
        rows.append({
            "tick": tick, "seed": seed,
            "input_hash": input_hash(tick, seed, signal_q, obstacle, pkt_loss),
            "decision": decide(signal_q, obstacle, pkt_loss),
            "latency_us": 0,  # host placeholder; device writes measured micros
        })
    return rows


def to_csv(rows) -> str:
    out = ["tick,seed,input_hash,decision,latency_us"]
    out += [f"{r['tick']},{r['seed']},{r['input_hash']},{r['decision']},{r['latency_us']}"
            for r in rows]
    return "\n".join(out) + "\n"


def parity(host_rows, device_rows) -> dict:
    """Compare host twin vs device journal rows (latency ignored).

    A length mismatch is a journal-completeness failure: parity is
    reported as None, never as a truncated-prefix 1.0.
    """
    mismatch = len(host_rows) != len(device_rows)
    n = min(len(host_rows), len(device_rows))
    hash_bad = sum(1 for i in range(n)
                   if host_rows[i]["input_hash"] != device_rows[i]["input_hash"])
    dec_bad = sum(1 for i in range(n)
                  if host_rows[i]["decision"] != device_rows[i]["decision"])
    agree = n - max(hash_bad, dec_bad) if not mismatch else 0
    return {"compared": n, "agree": agree if not mismatch else 0,
            "parity": None if mismatch or not n else round(agree / n, 4),
            "length_mismatch": mismatch,
            "hash_mismatches": hash_bad, "decision_mismatches": dec_bad,
            "host_rows": len(host_rows), "device_rows": len(device_rows)}
