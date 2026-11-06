"""Commitment strategy: fleet size, reserve, and operational horizon.

Pre-registered in docs/experiments/commitment-strategy-preregistration.md.
A deliberately small, transparent policy simulator: it is not the Korvo
planner, not firmware, and not evidence about a physical aircraft.

Question: is parking a fixed reserve (currently 2 of 16 in the shared
recon model) optimal, or should commitment rotate, escalate, or go
all-out when the operation - not just the first mission - is scored?
Metrics keep search success and residual fleet capability separate;
the illustrative utility is reported only with its formula.
"""
from __future__ import annotations

import math
import random
import statistics

NODES = 16
TILES = 192
SORTIES = 12
LAUNCH_MIN = 30
RECHARGE = 25
START_BATTERY = 100
NEAR_COST, FAR_COST = 30, 45
DAMAGE_P, LOSS_P = 0.012, 0.004
BASE_OVERLAP = 0.055
BASE_DETECT = 0.85
TILES_PER_NODE = 3


def _policy(name, kind, target, posture="near"):
    return {"name": name, "kind": kind, "target": target, "posture": posture}


POLICIES = tuple(
    [_policy(f"fixed-{k}-hold", "hold", k) for k in (1, 2, 4, 8, 12, 14, 16)]
    + [_policy(f"target-{k}-rotate", "rotate", k) for k in (8, 14)]
    + [_policy("escalate-4-16", "escalate", 4)]
    + [_policy("fixed-8-hold-far", "hold", 8, "far"),
       _policy("target-14-rotate-far", "rotate", 14, "far"),
       _policy("escalate-4-16-far", "escalate", 4, "far")]
)
POLICY_BY_NAME = {p["name"]: p for p in POLICIES}


def _select(nodes, policy, target):
    """Node indices launched this sortie under the policy."""
    charged = [i for i, n in enumerate(nodes)
               if n["serviceable"] and n["battery"] >= LAUNCH_MIN]
    if policy["kind"] == "hold":
        pool = [i for i in charged if i < policy["target"]]
        return pool[:target]
    pool = sorted(charged, key=lambda i: (-nodes[i]["battery"], i))
    return pool[:target]


def run_seed_commitment(seed, policy, overlap=BASE_OVERLAP,
                        detect_p=BASE_DETECT, hazard_mult=1.0):
    if isinstance(policy, str):
        policy = POLICY_BY_NAME[policy]
    rng = random.Random(seed)
    survivor = rng.randrange(TILES)
    nodes = [{"battery": START_BATTERY, "serviceable": True}
             for _ in range(NODES)]
    unsearched = set(range(TILES))
    far = policy["posture"] == "far"
    cost = FAR_COST if far else NEAR_COST
    dmg_p = DAMAGE_P * hazard_mult * (2 if far else 1)
    loss_p = LOSS_P * hazard_mult * (2 if far else 1)
    target = policy["target"]
    unsuccessful = 0
    found, find_sortie, readiness = False, None, None
    node_sorties = damaged = lost = searched = 0

    for sortie in range(1, SORTIES + 1):
        active = _select(nodes, policy, target)
        node_sorties += len(active)
        if active:
            nominal = len(active) * TILES_PER_NODE * (1.5 if far else 1.0)
            unique = int(round(nominal * math.exp(-overlap * (len(active) - 1))))
            unique = max(0, min(unique, len(unsearched)))
            sampled = rng.sample(sorted(unsearched), unique) if unique else []
            unsearched.difference_update(sampled)
            searched += len(sampled)
            detect_roll = rng.random()
            if survivor in sampled and detect_roll < detect_p:
                found, find_sortie = True, sortie
        active_set = set(active)
        for i, n in enumerate(nodes):
            if i in active_set:
                n["battery"] = max(0, n["battery"] - cost)
                r_loss, r_dmg = rng.random(), rng.random()
                if r_loss < loss_p:
                    n["serviceable"] = False
                    lost += 1
                elif r_dmg < dmg_p:
                    n["serviceable"] = False
                    damaged += 1
            elif n["serviceable"]:
                n["battery"] = min(START_BATTERY, n["battery"] + RECHARGE)
        if sortie == 6 or found:
            if readiness is None:
                readiness = sum(1 for n in nodes
                                if n["serviceable"] and n["battery"] >= LAUNCH_MIN)
        if found:
            break
        unsuccessful += 1
        if policy["kind"] == "escalate":
            target = min(NODES, 4 + 4 * (unsuccessful // 2))

    serviceable = [n for n in nodes if n["serviceable"]]
    utility = ((100 if found else 0) - 8 * lost - 3 * damaged
               - 0.25 * node_sorties)
    return {
        "found": found,
        "found_by_4": bool(found and find_sortie is not None and find_sortie <= 4),
        "find_sortie": find_sortie,
        "coverage_fraction": round(searched / TILES, 4),
        "node_sorties": node_sorties,
        "damaged": damaged,
        "lost": lost,
        "serviceable_end": len(serviceable),
        "mean_battery_serviceable_end": (
            round(statistics.fmean(n["battery"] for n in serviceable), 2)
            if serviceable else 0.0),
        "readiness_6_or_end": readiness if readiness is not None else sum(
            1 for n in nodes if n["serviceable"] and n["battery"] >= LAUNCH_MIN),
        "utility": round(utility, 2),
    }


def _aggregate(per_seed):
    found_sorties = sorted(p["find_sortie"] for p in per_seed
                           if p["find_sortie"] is not None)
    n = len(per_seed)
    def mean(key):
        return round(statistics.fmean(p[key] for p in per_seed), 4)
    return {
        "seeds": n,
        "found_rate": round(sum(p["found"] for p in per_seed) / n, 4),
        "found_by_4_rate": round(sum(p["found_by_4"] for p in per_seed) / n, 4),
        "mean_find_sortie_found_only": (
            round(statistics.fmean(found_sorties), 3) if found_sorties else None),
        "median_find_sortie_found_only": (
            statistics.median(found_sorties) if found_sorties else None),
        "mean_coverage_fraction": mean("coverage_fraction"),
        "mean_node_sorties": mean("node_sorties"),
        "mean_damaged": mean("damaged"),
        "mean_lost": mean("lost"),
        "mean_serviceable_end": mean("serviceable_end"),
        "mean_battery_serviceable_end": mean("mean_battery_serviceable_end"),
        "mean_readiness_6_or_end": mean("readiness_6_or_end"),
        "mean_utility": mean("utility"),
    }


def run_commitment(seeds, policies=POLICIES, **params):
    seeds = list(seeds)
    out = {}
    for policy in policies:
        per_seed = [run_seed_commitment(s, policy, **params) for s in seeds]
        out[policy["name"]] = _aggregate(per_seed)
    return out


SENSITIVITY_POLICIES = ("fixed-8-hold", "fixed-14-hold", "fixed-16-hold",
                        "target-14-rotate", "escalate-4-16")


def run_sensitivity(seeds):
    """Declared sweeps: overlap, detection, hazard multiplier."""
    seeds = list(seeds)
    policies = [POLICY_BY_NAME[n] for n in SENSITIVITY_POLICIES]
    out = {"overlap": {}, "detect_p": {}, "hazard_mult": {}}
    for value in (0.0, BASE_OVERLAP, 0.11):
        out["overlap"][str(value)] = run_commitment(
            seeds, policies, overlap=value)
    for value in (0.70, BASE_DETECT, 0.95):
        out["detect_p"][str(value)] = run_commitment(
            seeds, policies, detect_p=value)
    for value in (0.5, 1.0, 2.0):
        out["hazard_mult"][str(value)] = run_commitment(
            seeds, policies, hazard_mult=value)
    return out
