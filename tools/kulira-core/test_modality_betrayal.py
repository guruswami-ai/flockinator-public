from kulira_core.modality_betrayal import run_experiment, run_seed

def test_deterministic():
    assert run_seed(5, "modality") == run_seed(5, "modality")

def test_static_arm_takes_the_most_post_betrayal_damage():
    out = run_experiment(range(20))
    assert out["static"]["dangerous"] > out["modality"]["dangerous"]
    assert out["static"]["dangerous"] > out["node"]["dangerous"]

def test_modality_trust_discounts_ir_promptly():
    out = run_experiment(range(20))
    assert out["modality"]["median_discount_contacts"] is not None
    assert out["modality"]["median_discount_contacts"] <= 15

def test_node_trust_pays_recall_for_pooled_blame():
    out = run_experiment(range(20))
    assert out["node"]["mean_recall"] <= out["modality"]["mean_recall"]
