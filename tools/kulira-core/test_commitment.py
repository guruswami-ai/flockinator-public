from kulira_core.commitment import (
    POLICIES, POLICY_BY_NAME, run_commitment, run_seed_commitment,
    run_sensitivity)


def test_deterministic_same_seed():
    a = run_seed_commitment(7, "fixed-14-hold")
    b = run_seed_commitment(7, "fixed-14-hold")
    assert a == b


def test_all_out_launches_whole_fleet_first_sortie():
    result = run_seed_commitment(3, "fixed-16-hold")
    assert result["node_sorties"] >= 16


def test_single_node_never_launches_more_than_one_per_sortie():
    result = run_seed_commitment(3, "fixed-1-hold")
    assert result["node_sorties"] <= 12


def test_fleet_accounting_closes():
    for name in POLICY_BY_NAME:
        r = run_seed_commitment(11, name)
        assert r["serviceable_end"] + r["damaged"] + r["lost"] == 16
        assert 0.0 <= r["coverage_fraction"] <= 1.0
        assert r["readiness_6_or_end"] <= 16


def test_policy_registry_shape():
    far = POLICY_BY_NAME["target-14-rotate-far"]
    assert far["posture"] == "far" and far["kind"] == "rotate"
    assert len(POLICIES) == 13


def test_aggregate_rates_are_probabilities():
    out = run_commitment(range(8), policies=[POLICY_BY_NAME["fixed-8-hold"]])
    row = out["fixed-8-hold"]
    assert 0.0 <= row["found_rate"] <= 1.0
    assert 0.0 <= row["found_by_4_rate"] <= row["found_rate"]


def test_sensitivity_sweeps_declared_axes():
    out = run_sensitivity(range(4))
    assert set(out) == {"overlap", "detect_p", "hazard_mult"}
    assert set(out["overlap"]) == {"0.0", "0.055", "0.11"}
    for axis in out.values():
        for policies in axis.values():
            assert "target-14-rotate" in policies
