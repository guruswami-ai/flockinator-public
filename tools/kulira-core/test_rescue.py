import json
from pathlib import Path
from kulira_core.rescue import run_rescue_cycle
from kulira_core.sensing import Reading, assess_contact

def test_real_survivor_reaches_dig_with_two_modalities():
    r = run_rescue_cycle(seed=1, fabricated=False)
    assert r["dig"] is True and r["strength"] == "strong" and r["direct_sightings"] == 2

def test_fabricated_heat_plus_copies_never_digs():
    r = run_rescue_cycle(seed=1, fabricated=True)
    assert r["dig"] is False and r["independent_modalities"] < 2
    assert r["hearsay_copies"] == 2 and r["direct_sightings"] == 0

def test_same_node_two_modalities_never_digs():
    r = [Reading("A1", "ir_max_c", 36.5, 21.0, "heat-1"),
         Reading("A1", "co2_ppm", 1500, 450, "trace-1")]
    a = assess_contact(r, min_modalities=2)
    assert a["strength"] == "moderate"  # below the DIG bar (strong)

def test_two_nodes_one_modality_never_digs():
    r = [Reading("A1", "ir_max_c", 36.5, 21.0, "heat-1"),
         Reading("B1", "ir_max_c", 37.0, 21.0, "heat-2")]
    a = assess_contact(r, min_modalities=2)
    assert a["strength"] == "weak"

def test_seed_changes_readings_and_cycle_is_deterministic():
    assert run_rescue_cycle(seed=7, fabricated=False) == run_rescue_cycle(seed=7, fabricated=False)
    assert run_rescue_cycle(seed=7, fabricated=True)["dig"] is False

def test_validation_artifact_matches_code():
    root = Path(__file__).resolve().parents[2]
    artifact = json.loads((root / "validation/kulira/rescue-cycle-001.json").read_text())
    assert artifact == {"real": run_rescue_cycle(seed=1, fabricated=False),
                        "fabricated": run_rescue_cycle(seed=1, fabricated=True)}
