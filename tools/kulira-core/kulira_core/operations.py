"""Fleet commitment / reserve strategy screen (pre-registered).

Transparent seeded simulator: mission-level discovery vs
operational-level residual capability. A fleet of 16 flies up to 4
sequential incidents in one daylight window. Strategies differ only
in how many aircraft they commit, whether they rotate the roster,
and whether they escalate from reserve. Metrics are reported as a
Pareto pair (survivors found, ready aircraft at window end) plus
losses; no blended score. Stdlib only, seed = one operation window.
See docs/experiments/operations-reserve-preregistration.md.
"""
from __future__ import annotations

import random

FLEET = 16
AREA = 576
CELLS_PER_TURN = 6
DAYLIGHT = 240
MAX_INCIDENTS = 4
RECHARGE = 12
TACTICAL_RESERVE = 15.0
RETURN_COST = {"near": 4.0, "mid": 8.0, "far": 14.0}

# name -> (initial launch count, escalation count or None, rotate)
STRATEGIES = {
    "K1": (1, None, False),
    "K2": (2, None, False),
    "K4": (4, None, False),
    "K8": (8, None, False),
    "K8R": (8, None, True),
    "K14": (14, None, False),
    "K16": (16, None, False),
    "ESC": (4, 8, False),
}
ESCALATE_TURN = 20


def _new_fleet():
    return [{"id": i, "battery": 100.0, "state": "ready",
             "repair_at": -1, "last_flown": -1} for i in range(FLEET)]


def run_operation(seed: int, strategy: str, p_detect: float = 0.7,
                  p_fail: float = 0.002, far_frac: float = 0.15,
                  overlap: float = 0.0) -> dict:
    k0, esc_k, rotate = STRATEGIES[strategy]
    rng = random.Random(seed)
    fleet = _new_fleet()
    daylight = DAYLIGHT
    found = attempted = unattempted = 0
    find_turns = []
    damaged_events = lost = 0
    ready_before_2nd = None

    for inc in range(MAX_INCIDENTS):
        for a in fleet:  # repairs complete at incident boundary
            if a["state"] == "damaged" and inc >= a["repair_at"]:
                a["state"], a["battery"] = "ready", 60.0
        ready = [a for a in fleet if a["state"] == "ready"]
        if inc == 1:
            ready_before_2nd = len(ready)
        if not ready or daylight <= 0:
            unattempted += 1
            continue
        attempted += 1
        if rotate:
            ready.sort(key=lambda a: (a["last_flown"], -a["battery"], a["id"]))
        else:
            ready.sort(key=lambda a: (-a["battery"], a["id"]))
        airborne = ready[:min(k0, len(ready))]
        for a in airborne:
            a["state"], a["last_flown"] = "airborne", inc

        r = rng.random()
        # distance mix: near 55%, far = far_frac, mid = remainder
        dist = "near" if r < 0.55 else ("far" if r > 1.0 - far_frac else "mid")
        pos = rng.randrange(AREA)
        frontier = 0.0
        turn = 0
        escalated = False
        found_this = False
        while daylight > 0 and airborne:
            turn += 1
            daylight -= 1
            if esc_k and not escalated and turn >= ESCALATE_TURN:
                escalated = True
                spare = [a for a in fleet if a["state"] == "ready"]
                spare.sort(key=lambda a: (-a["battery"], a["id"]))
                for a in spare[:esc_k]:
                    a["state"], a["last_flown"] = "airborne", inc
                    airborne.append(a)
            frontier += len(airborne) * CELLS_PER_TURN * (1.0 - overlap)
            while frontier >= pos + 1:
                if rng.random() < p_detect:
                    found_this = True
                    break
                frontier -= AREA  # missed pass; re-sweep next pass
            if found_this:
                break
            survivors = []
            for a in airborne:
                a["battery"] -= 1.1
                if rng.random() < p_fail:
                    a["state"] = "damaged"
                    a["repair_at"] = inc + 2
                    damaged_events += 1
                    continue
                if a["battery"] - RETURN_COST[dist] < TACTICAL_RESERVE:
                    a["battery"] -= RETURN_COST[dist]
                    if a["battery"] < 0:  # forced landing
                        roll = rng.random()
                        if roll < 0.1:
                            a["state"] = "lost"
                            lost += 1
                            continue
                        if roll < 0.6:
                            a["state"] = "damaged"
                            a["repair_at"] = inc + 2
                            damaged_events += 1
                            continue
                        a["battery"] = 0.0
                    a["state"] = "ready"
                    continue
                survivors.append(a)
            airborne = survivors
        for a in airborne:  # found / daylight end: everyone still up lands
            a["battery"] = max(0.0, a["battery"] - RETURN_COST[dist])
            a["state"] = "ready"
        if found_this:
            found += 1
            find_turns.append(turn)
        for a in fleet:  # inter-incident recharge
            if a["state"] == "ready":
                a["battery"] = min(100.0, a["battery"] + RECHARGE)

    ready_end = [a for a in fleet if a["state"] == "ready"]
    return {
        "strategy": strategy, "seed": seed, "found": found,
        "attempted": attempted, "unattempted": unattempted,
        "mean_find_turns": round(sum(find_turns) / len(find_turns), 2) if find_turns else None,
        "ready_end": len(ready_end),
        "mean_ready_battery": round(sum(a["battery"] for a in ready_end) / len(ready_end), 1) if ready_end else 0.0,
        "damaged_events": damaged_events, "lost": lost,
        "ready_before_2nd": ready_before_2nd,
        "daylight_left": daylight,
    }


def run_operations(seeds, strategies=tuple(STRATEGIES), **params) -> dict:
    out = {}
    for name in strategies:
        rows = [run_operation(s, name, **params) for s in seeds]
        n = len(rows)
        inc = MAX_INCIDENTS * n
        out[name] = {
            "per_seed": rows,
            "mean_found": round(sum(r["found"] for r in rows) / n, 3),
            "find_rate": round(sum(r["found"] for r in rows) / inc, 4),
            "unattempted": sum(r["unattempted"] for r in rows),
            "mean_ready_end": round(sum(r["ready_end"] for r in rows) / n, 2),
            "mean_ready_battery": round(sum(r["mean_ready_battery"] for r in rows) / n, 1),
            "damaged_events": sum(r["damaged_events"] for r in rows),
            "lost": sum(r["lost"] for r in rows),
            "mean_find_turns": round(
                sum(r["mean_find_turns"] for r in rows if r["mean_find_turns"] is not None)
                / max(1, sum(1 for r in rows if r["mean_find_turns"] is not None)), 2),
        }
    return out


def pareto_frontier(agg: dict) -> list[str]:
    """Strategies not dominated on (find_rate up, ready_end up)."""
    front = []
    for name, a in agg.items():
        dominated = any(
            b["find_rate"] >= a["find_rate"] and b["mean_ready_end"] >= a["mean_ready_end"]
            and (b["find_rate"] > a["find_rate"] or b["mean_ready_end"] > a["mean_ready_end"])
            for other, b in agg.items() if other != name)
        if not dominated:
            front.append(name)
    return sorted(front)
