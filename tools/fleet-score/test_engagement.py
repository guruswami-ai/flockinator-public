"""Synthetic instrumentation checks; no experiment runs or inferred effects."""
import copy
import json
import pathlib
import subprocess
import sys

import pytest

from engagement import SCHEMA, audit


def evidence(**updates):
    record = {"schema": SCHEMA, "run": "synthetic-001", "seed": 0,
              "treatment": "T4", "designated_unit": "A1", "start_turn": 30,
              "complete": True, "observations": []}
    record.update(updates)
    return record


def observation(**updates):
    row = {"id": "obs-1", "unit": "A1", "turn": 30, "truth": "hazard",
           "untreated_label": "hazard", "treated_label": "survivor",
           "applied": True}
    row.update(updates)
    return row


def test_positive_commits_do_not_establish_opportunity():
    # Extraneous policy outcomes cannot change the evidence status.
    result = audit(evidence(commits=13))
    assert result["status"] == "NO_OPPORTUNITY"
    assert result["opportunities"] == result["applied"] == 0


def test_engaged_without_commits():
    result = audit(evidence(observations=[observation()], commits=0))
    assert result["status"] == "ENGAGED"
    assert result["opportunities"] == result["applied"] == result["labels_changed"] == 1


def test_no_application_and_natural_error_are_not_engagement():
    result = audit(evidence(observations=[observation(
        applied=False, untreated_label="survivor")]))
    assert result["opportunities"] == 1
    assert result["status"] == "NOT_EXERCISED"
    assert result["labels_changed"] == result["applied"] == 0


def test_applied_does_not_necessarily_change_a_label():
    result = audit(evidence(observations=[observation(untreated_label="survivor")]))
    assert result["status"] == "ENGAGED"
    assert result["applied"] == 1
    assert result["labels_changed"] == 0


def test_partial_evidence_never_establishes_engagement():
    result = audit(evidence(complete=False, observations=[observation()]))
    assert result["status"] == "UNMEASURED"


def test_boundary_and_designated_unit_define_opportunities():
    rows = [observation(id="early", turn=29, applied=False, treated_label="hazard"),
            observation(id="other", unit="B1", applied=False, treated_label="hazard"),
            observation(id="survivor", truth="survivor", untreated_label="survivor", applied=False),
            observation()]
    result = audit(evidence(observations=rows))
    assert result["opportunities"] == result["applied"] == 1
    assert audit(evidence(treatment="T3", start_turn=0, observations=[
        observation(turn=0)]))["status"] == "ENGAGED"


@pytest.mark.parametrize("updates", [
    {"turn": 29}, {"unit": "B1"}, {"truth": "survivor"},
    {"treated_label": "hazard"}, {"applied": False},
    {"turn": True}, {"turn": -1}, {"turn": 30.0}, {"id": ""},
    {"applied": 1}, {"truth": []}, {"unit": None},
])
def test_invalid_observation_rejected(updates):
    with pytest.raises(ValueError):
        audit(evidence(observations=[observation(**updates)]))


@pytest.mark.parametrize("updates", [
    {"seed": True}, {"seed": -1}, {"complete": 1},
    {"schema": "unknown"}, {"treatment": "T0"},
    {"start_turn": -1}, {"treatment": "T3", "start_turn": 30},
    {"observations": None}, {"observations": [None]},
    {"observations": [observation(), observation()]},
])
def test_invalid_envelope_rejected(updates):
    with pytest.raises(ValueError):
        audit(evidence(**updates))


def test_missing_application_metadata_is_not_reconstructed():
    row = observation()
    del row["applied"]
    with pytest.raises(ValueError, match="applied"):
        audit(evidence(observations=[row]))


def test_audit_is_nonmutating_and_order_independent():
    source = evidence(observations=[observation(), observation(id="obs-2")])
    original = copy.deepcopy(source)
    result = audit(source)
    assert source == original
    source["observations"].reverse()
    assert audit(source) == result


def test_cli_status_and_missing_evidence(tmp_path):
    script = pathlib.Path(__file__).with_name("engagement.py")
    path = tmp_path / "evidence.json"
    def run():
        return subprocess.run([sys.executable, str(script), str(path)],
                              capture_output=True, text=True, check=False)
    missing = run()
    assert missing.returncode == 3
    assert json.loads(missing.stdout)["status"] == "ERROR"
    for payload, code, status in ((evidence(), 2, "NO_OPPORTUNITY"),
            (evidence(complete=False), 2, "UNMEASURED"),
            (evidence(observations=[observation()]), 0, "ENGAGED")):
        path.write_text(json.dumps(payload))
        result = run()
        assert result.returncode == code
        assert json.loads(result.stdout)["status"] == status
