"""Structural controls and truth boundary, not new experimental evidence."""
import copy
import json

import pytest

from kulira_core.feedback_matched import main, score_sequence_matched
from kulira_core.feedback_trust import score_sequence_feedback
from kulira_core.relay_attack import NODES


def fixture(truths):
    return [{"contact": i, "truth": truth, "reports": [
        (f"s{i}-0", "A1", "ir", "survivor", False),
        (f"s{i}-1", "A2", "co2", "survivor", False),
        (f"s{i}-2", "B1", "sound", "hazard", False),
    ]} for i, truth in enumerate(truths)]


def test_f2_equals_e_for_every_eight_report_label_count():
    # Covers every possible survivor/hazard count with up to eight reports,
    # including no reports and the two-survivor/one-hazard counterexample.
    for size in range(9):
        for survivors in range(size+1):
            reports = [(f"s{j}", NODES[j], "ir", "survivor" if j < survivors else "hazard", False)
                       for j in range(size)]
            seq = [{"contact": 0, "truth": "hazard", "reports": reports}]
            out = score_sequence_matched(seq, start=0, stop=1)
            expected = survivors >= 2 and 2*survivors-size >= 2
            assert out["arms"]["F2"]["decision_log"] == [expected]
            assert out["arms"]["L2"]["decision_log"] == [expected]
    out = score_sequence_matched(fixture(["hazard"]), start=0, stop=1)
    assert out["arms"]["F1"]["decision_log"] == [True]
    assert out["arms"]["F2"]["decision_log"] == [False]


@pytest.mark.parametrize("delay", [0, 3, 15])
def test_l1_compatibility_and_reveal_boundary_with_positive_control(delay):
    first_change = max(1, delay)
    a = fixture(["hazard"]+["survivor"]*first_change)
    b = fixture(["survivor"]*(first_change+1))
    out_a = score_sequence_matched(a, delay, start=0, stop=len(a))
    out_b = score_sequence_matched(b, delay, start=0, stop=len(b))
    log_a = out_a["arms"]["L1"]["decision_log"]
    log_b = out_b["arms"]["L1"]["decision_log"]
    for arm in out_a["arms"]:
        assert out_a["arms"][arm]["decision_log"][:first_change] == out_b["arms"][arm]["decision_log"][:first_change]
    assert log_a[first_change] is False and log_b[first_change] is True
    assert log_a == score_sequence_feedback(a, "REP", delay=delay)["decision_log"]
    assert out_a["reveal_mask"] == out_b["reveal_mask"]
    assert out_a["shared_budget"] == out_b["shared_budget"]


def test_frozen_receives_same_reveals_without_updates_and_is_truth_invariant():
    a = fixture(["hazard"]*5)
    b = fixture(["survivor"]*5)
    original = copy.deepcopy(a)
    first = score_sequence_matched(a, start=0, stop=5)
    second = score_sequence_matched(b, delay=3, availability=0.25, start=0, stop=5)
    assert a == original
    for arm in ("F1", "F2"):
        assert first["arms"][arm]["decision_log"] == second["arms"][arm]["decision_log"]
        assert all(w == 1 for w in first["arms"][arm]["final_weights_after_flush"].values())
        assert first["arms"][arm]["weight_update_applications_before_decisions"] == 0
        assert first["arms"][arm]["processed_report_reveals_before_decisions"] == 12
    assert first["arms"]["L1"]["weight_update_applications_before_decisions"] == 12
    assert first["shared_budget"]["post_horizon_flush"] == 3


def test_unavailable_truth_cannot_change_any_decision():
    a = fixture(["hazard"]*5)
    b = fixture(["survivor"]*5)
    one = score_sequence_matched(a, availability=0, start=0, stop=5)
    two = score_sequence_matched(b, availability=0, start=0, stop=5)
    for arm in one["arms"]:
        assert one["arms"][arm]["decision_log"] == two["arms"][arm]["decision_log"]
        assert one["arms"][arm]["final_weights_after_flush"] == two["arms"][arm]["final_weights_after_flush"]


def test_duplicate_admission_same_window_rates_and_paired_interaction():
    seq = fixture(["hazard", "survivor", "hazard", "survivor"])
    baseline = score_sequence_matched(seq, availability=0, start=2, stop=4)
    seq[0]["reports"].append(seq[0]["reports"][0])
    assert score_sequence_matched(seq, availability=0, start=2, stop=4) == baseline
    row = baseline["arms"]["F1"]["metrics"]
    assert row == dict(contacts=2, hazards=1, survivors=1, dangerous=1,
                       found=1, commits=2, abstentions=0, harm_rate=1, recall=1, coverage=1)
    for contrast in ("L1_minus_F1", "L2_minus_F2", "updating_by_margin_interaction"):
        assert all(v == 0 for v in baseline["paired_contrasts"][contrast].values())
    assert baseline["paired_contrasts"]["L2_minus_L1"]["coverage"] == -1
    no_survivor = score_sequence_matched(fixture(["hazard"]), start=0, stop=1)
    assert no_survivor["paired_contrasts"]["L1_minus_F1"]["recall"] is None


@pytest.mark.parametrize("kw", [dict(delay=True), dict(delay=-1),dict(availability=float("nan")),
                                 dict(availability=True), dict(availability=2),dict(reveal_seed=True),
                                 dict(start=True),dict(stop=7)])
def test_invalid_parameters_reject(kw):
    args = dict(start=0, stop=1)
    args.update(kw)
    with pytest.raises(ValueError):
        score_sequence_matched(fixture(["hazard"]), **args)


def test_unknown_reporter_or_noncontiguous_contact_reject():
    seq = fixture(["hazard"])
    seq[0]["reports"][0] = ("x", "unknown", "ir", "survivor", False)
    with pytest.raises(ValueError):
        score_sequence_matched(seq, start=0, stop=1)
    seq = fixture(["hazard"])
    seq[0]["contact"] = True
    with pytest.raises(ValueError):
        score_sequence_matched(seq, start=0, stop=1)


def test_cli_historical_only_is_deterministic_and_refuses_overwrite(tmp_path):
    first, second = tmp_path/"first.json", tmp_path/"second.json"
    main(["--historical-smoke", "--out", str(first)])
    main(["--historical-smoke", "--out", str(second)])
    assert first.read_bytes() == second.read_bytes()
    report = json.loads(first.read_text())
    assert report["historical_arm_comparisons"] == 240
    assert report["exposed_seeds"] == list(range(220,260))
    saved = first.read_bytes()
    with pytest.raises(SystemExit) as exc:
        main(["--historical-smoke", "--out", str(first)])
    assert exc.value.code == 2 and first.read_bytes() == saved
    with pytest.raises(SystemExit):
        main(["--out", str(tmp_path/"missing-mode.json")])
