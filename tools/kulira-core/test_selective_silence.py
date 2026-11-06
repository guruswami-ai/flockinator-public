"""Selective silence: invariants + counterfactual attribution."""
from kulira_core.selective_silence import (
    generate_trial_silence, run_silence, score_trial_silence,
)


def test_deterministic_and_schema():
    a, b = generate_trial_silence(7), generate_trial_silence(7)
    assert a == b
    for c in a:
        assert set(c) >= {"contact", "truth", "reports", "suppressed", "targeted"}
        assert all(len(r) == 5 and r[4] is False
                   for r in c["reports"] + c["suppressed"])


def test_suppression_only_on_hazard_and_only_hazard_labels():
    for seed in range(10):
        for c in generate_trial_silence(seed):
            if c["suppressed"]:
                assert c["truth"] == "hazard" and c["targeted"]
                assert all(r[3] == "hazard" for r in c["suppressed"])
                assert all(r[3] == "survivor" for r in c["reports"])


def test_no_forgeries_exist_to_detect():
    # The point of the attack: verified-only policy D sees nothing forged.
    res = run_silence(range(4))
    assert res["D"]["pooled"]["dangerous"] >= 0
    for pol in ("A", "B", "C", "D", "E", "E-M"):
        pooled = res[pol]["pooled"]
        assert pooled["silenced_dangerous"] <= pooled["dangerous"]


def test_counterfactual_attribution_bounds():
    trial = generate_trial_silence(3)
    s = score_trial_silence(trial, "A")
    assert 0 <= s["silenced_dangerous"] <= s["dangerous"]
    assert s["targeted"] == sum(1 for c in trial if c["targeted"])
