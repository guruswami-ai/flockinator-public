import pytest

from kulira_core.canary_score import load_device_csv, score_journal
from kulira_core.twin import WAIT, missing_hash, run_twin, to_csv


def test_perfect_journal_scores_parity_one():
    rows = run_twin(80, 100, p_loss=0.0)
    dev = load_device_csv(to_csv(rows))
    rep = score_journal(dev, ticks=100)["80"]
    assert rep["parity"] == 1.0 and not rep["link_failure"]


def test_missing_rows_counted_not_failed():
    rows = run_twin(80, 100, p_loss=0.0)
    for i in (10, 20, 30):
        rows[i] = {**rows[i], "input_hash": missing_hash(rows[i]["tick"], 80),
                   "decision": WAIT}
    rep = score_journal(load_device_csv(to_csv(rows)), ticks=100)["80"]
    assert rep["parity"] == 1.0 and rep["missing_input_rows"] == 3


def test_truncated_journal_is_failure_not_score():
    rows = run_twin(80, 100, p_loss=0.0)[:90]
    rep = score_journal(load_device_csv(to_csv(rows)), ticks=100)["80"]
    assert rep["parity"] is None and rep["length_mismatch"]


def test_bad_header_rejected():
    with pytest.raises(ValueError):
        load_device_csv("a,b,c\n1,2,3\n")
