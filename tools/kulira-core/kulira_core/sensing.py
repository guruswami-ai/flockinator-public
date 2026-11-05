"""Rescue sensing from real node sensors (Kulira-owned analysis layer).

Nodes already poll SHTC3 temperature/humidity, QMI8658 accel/gyro, and
RTC (firmware/node-platform sensors.cpp, exposed as JSON). Thermal/IR
arrays and CO2 modules are add-on sensors; this layer treats every
modality uniformly: a reading is evidence only relative to a local
baseline, and a contact is strong only when independent nodes and
distinct modalities agree. That is the multi-modal version of the
corroboration rule: two modalities, like two sightings, must be
independent to count.
"""
from __future__ import annotations
from dataclasses import dataclass

# per-modality anomaly thresholds (delta from baseline) - deliberately
# plain, tunable per scenario, never hidden in a model
THRESHOLDS = {"temperature_c": 2.0, "humidity_percent": 8.0,
              "co2_ppm": 400.0, "accel_m_s2": 2.0, "gyro_deg_s": 30.0,
              "sound_db": 6.0, "ir_max_c": 3.0}
SURVIVOR_MODALITIES = {"temperature_c", "co2_ppm", "ir_max_c", "sound_db", "humidity_percent"}

@dataclass(frozen=True)
class Reading:
    node: str; modality: str; value: float; baseline: float; sighting_id: str

def _anomalous(r: Reading) -> bool:
    return abs(r.value - r.baseline) >= THRESHOLDS.get(r.modality, float("inf"))

def assess_contact(readings, min_modalities: int = 2) -> dict:
    hits = [r for r in readings if _anomalous(r)]
    modalities = sorted({r.modality for r in hits})
    nodes = sorted({r.node for r in hits})
    kind = "survivor_candidate" if any(m in SURVIVOR_MODALITIES for m in modalities) else "unknown"
    if any(r.modality in ("accel_m_s2", "gyro_deg_s") for r in hits) and not any(m in SURVIVOR_MODALITIES for m in modalities):
        kind = "disturbance"
    if not hits:
        strength = "none"
    elif len(modalities) >= min_modalities and len(nodes) >= 2:
        strength = "strong"
    elif len(modalities) >= min_modalities:
        strength = "moderate"
    else:
        strength = "weak"
    return {"strength": strength, "modalities": modalities,
            "independent_nodes": len(nodes), "nodes": nodes, "kind_hint": kind}
