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


def missing_hash(tick: int, seed: int) -> str:
    """Journal hash for a tick with no received input (contract v1.1).

    The device cannot hash inputs it never received; it journals
    this canonical marker with decision WAIT. Parity counts such
    rows as missing-input rows, not hash mismatches.
    """
    h = 0x811C9DC5
    for b in f"missing:{tick}:{seed}".encode():
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"


def tick_inputs(seed: int, ticks: int, p_loss: float = P_LOSS,
                p_obs: float = P_OBS) -> list[dict]:
    """The broadcast input stream itself (firmware golden vectors).

    Exposes signal_q/obstacle/pkt_loss per tick so a device port
    can be fed identical inputs and its journal compared row by
    row. run_twin() is built on this; the two cannot drift.
    """
    rng_sig = random.Random(seed)
    rng_obs = random.Random(seed ^ 0x5BD1E995)
    rng_net = random.Random(seed ^ 0x27D4EB2D)
    out = []
    for tick in range(ticks):
        signal_q = int(rng_sig.uniform(0.0, 1.0) * 1000 + 0.5)
        out.append({"tick": tick, "seed": seed, "signal_q": signal_q,
                    "obstacle": rng_obs.random() < p_obs,
                    "pkt_loss": rng_net.random() < p_loss})
    return out


def run_twin(seed: int, ticks: int = 500, p_loss: float = P_LOSS,
             p_obs: float = P_OBS) -> list[dict]:
    # NOTE: input generation is host-side simulation of the broadcast
    # input stream; the device decides on inputs it receives, never
    # on its own RNG. Inputs come from tick_inputs() so the golden
    # vectors and the twin journal are the same stream by construction.
    rows = []
    for inp in tick_inputs(seed, ticks, p_loss, p_obs):
        rows.append({
            "tick": inp["tick"], "seed": seed,
            "input_hash": input_hash(inp["tick"], seed, inp["signal_q"],
                                     inp["obstacle"], inp["pkt_loss"]),
            "decision": decide(inp["signal_q"], inp["obstacle"], inp["pkt_loss"]),
            "latency_us": 0,  # host placeholder; device writes measured micros
        })
    return rows


def to_csv(rows) -> str:
    out = ["tick,seed,input_hash,decision,latency_us"]
    out += [f"{r['tick']},{r['seed']},{r['input_hash']},{r['decision']},{r['latency_us']}"
            for r in rows]
    return "\n".join(out) + "\n"


def distribution_sweep(seed: int, ticks: int = 2000,
                         losses=(0.0, 0.05, 0.10, 0.20)) -> dict:
    """Empirical vs analytic decision distribution per loss level."""
    out = {}
    for p in losses:
        rows = run_twin(seed, ticks, p_loss=p)
        n = len(rows)
        emp = {name: round(sum(1 for r in rows if r["decision"] == code) / n, 4)
               for name, code in (("SEARCH", SEARCH), ("DOUBLE_CHECK", DOUBLE_CHECK),
                                  ("WAIT", WAIT))}
        out[str(p)] = {"empirical": emp, "expected": expected_distribution(p)}
    return out


def parity(host_rows, device_rows) -> dict:
    """Compare host twin vs device journal rows (latency ignored).

    A length mismatch is a journal-completeness failure: parity is
    reported as None, never as a truncated-prefix 1.0.
    """
    mismatch = len(host_rows) != len(device_rows)
    n = min(len(host_rows), len(device_rows))

    def _is_missing(i):
        return device_rows[i]["input_hash"] == missing_hash(
            device_rows[i]["tick"], device_rows[i]["seed"])
    id_bad = sum(1 for i in range(n)
                 if host_rows[i]["tick"] != device_rows[i]["tick"]
                 or host_rows[i]["seed"] != device_rows[i]["seed"])
    hash_bad = sum(1 for i in range(n)
                   if not _is_missing(i)
                   and host_rows[i]["input_hash"] != device_rows[i]["input_hash"])
    dec_bad = sum(1 for i in range(n)
                  if host_rows[i]["decision"] != device_rows[i]["decision"])
    missing = sum(1 for i in range(n) if _is_missing(i))
    agree = sum(1 for i in range(n)
                if host_rows[i]["tick"] == device_rows[i]["tick"]
                and host_rows[i]["seed"] == device_rows[i]["seed"]
                and ((host_rows[i]["input_hash"] == device_rows[i]["input_hash"]
                      and host_rows[i]["decision"] == device_rows[i]["decision"])
                     or (device_rows[i]["input_hash"] == missing_hash(
                             device_rows[i]["tick"], device_rows[i]["seed"])
                         and device_rows[i]["decision"] == WAIT)))
    # Contract v1.1: strictly more than 50% missing = link failure,
    # reported as such, never as a numerical policy score.
    link_failure = n > 0 and missing / n > 0.5
    return {"compared": n, "agree": 0 if mismatch else agree,
            "missing_input_rows": missing, "link_failure": link_failure,
            "parity": None if mismatch or not n or link_failure
            else round(agree / n, 4),
            "length_mismatch": mismatch, "identity_mismatches": id_bad,
            "hash_mismatches": hash_bad, "decision_mismatches": dec_bad,
            "host_rows": len(host_rows), "device_rows": len(device_rows)}
