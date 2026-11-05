"""Seeded rescue cycle: HEAT/TRACE -> VERIFY -> DIG (or refuse).

Real-survivor case: two nodes, two modalities (thermal + CO2) agree.
Fabricated case: Kulira forges one heat sighting; two peers relay copies
of it. Copies travel through the bridge contract as hearsay_relayed -
they add reporters, never independent sightings - so VERIFY refuses DIG.
DIG requires >=2 modalities from >=2 independent nodes, counting only
direct_verified sighting IDs.
"""
from __future__ import annotations
import random
from .bridge import direct_sighting_ids, to_journal_events
from .sensing import Reading, assess_contact

def run_rescue_cycle(seed: int = 1, fabricated: bool = False) -> dict:
    rng = random.Random(seed)
    if fabricated:
        readings = [Reading("K1", "ir_max_c", 36.0 + rng.random(), 20.0, "heat-fake")]
        reports = [{"reporter": "K1", "sighting_id": "heat-fake", "verified": None, "claim": "survivor"}]
        # relayed copies: same sighting, other reporters, hearsay only
        for relay in ("B1", "C1"):
            reports.append({"reporter": relay, "sighting_id": "heat-fake",
                            "originator": "K1", "verified": None, "forwarded": True,
                            "origin_turn": 1, "claim": "survivor"})
    else:
        readings = [Reading("A1", "ir_max_c", 36.5 + rng.random(), 21.0, "heat-1"),
                    Reading("B1", "co2_ppm", 1500 + int(rng.random() * 100), 450, "trace-1")]
        reports = [{"reporter": r.node, "sighting_id": r.sighting_id,
                    "verified": True, "claim": "survivor"} for r in readings]
    events = to_journal_events(reports)
    direct = direct_sighting_ids(events)
    witnessed = [r for r in readings if r.sighting_id in direct]
    if fabricated:
        # the forged origin was never direct_verified, so nothing witnesses DIG
        witnessed = []
    a = assess_contact(witnessed, min_modalities=2)
    return {"seed": seed, "fabricated": fabricated,
            "dig": a["strength"] == "strong",
            "strength": a["strength"],
            "independent_modalities": len(a["modalities"]),
            "independent_nodes": a["independent_nodes"],
            "direct_sightings": len(direct),
            "hearsay_copies": sum(1 for e in events if e["auth_status"] == "hearsay_relayed"),
            "reason": ("two modalities, two independent nodes" if a["strength"] == "strong"
                       else "no direct_verified sighting; relayed copies are not witnesses")}
