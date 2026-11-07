import copy
import json

import pytest

from kulira_core.fault_eval import CELLS, SCHEMA, baseline, demo, main, score


def fixture():
    assignments = []
    for unit in ("u1", "u2"):
        for arm in ("wall", "dashboard"):
            for case in ("c1", "c2"):
                assignments.append(dict(trial_id=f"{unit}-{arm}-{case}", unit_id=unit,
                                        arm=arm, case_id=case, timeout_seconds=10))
    protocol = dict(schema=SCHEMA, evidence_kind="synthetic_smoke",
                    arms=["wall", "dashboard"], assignments=assignments)
    answers = dict(schema=SCHEMA, cases={"c1": ["A1"], "c2": []})
    responses = [dict(trial_id=a["trial_id"], status="completed", elapsed_seconds=2,
                      detected_nodes=answers["cases"][a["case_id"]]) for a in assignments]
    return protocol, answers, responses


def test_missing_timeout_error_are_not_dropped_or_counted_clean_correct():
    p, a, r = fixture()
    # Fault timeout, clean error, fault missing: all remain in denominators.
    r[0].update(status="timeout", detected_nodes=[], elapsed_seconds=10)
    r[1].update(status="error", detected_nodes=[], elapsed_seconds=1)
    r = [x for x in r if x["trial_id"] != "u2-wall-c1"]
    out = score(p, a, r)
    wall = out["arms"]["wall"]
    assert wall["scheduled"] == 4
    assert wall["exact_accuracy"] == .25
    assert wall["clean_correct_rate"] == .5
    assert wall["fault_localisation_rate"] == 0
    assert wall["mean_capped_time_to_correct_localisation"] == 10
    assert wall["status_counts"] == dict(completed=1, timeout=1, error=1, missing=1)
    assert out["paired"]["dashboard"]["units"] == 2
    assert out["paired"]["dashboard"]["mean_exact_accuracy_difference"] == .75


def test_wrong_localisation_is_detected_but_incorrect_and_clean_alarm_counts():
    p, a, r = fixture()
    r[0]["detected_nodes"] = ["B1"]
    r[1]["detected_nodes"] = ["A1"]
    result = score(p, a, r)["arms"]["wall"]
    assert result["fault_detection_rate"] == 1
    assert result["fault_localisation_rate"] == .5
    assert result["false_alarm_rate"] == .5
    assert result["mean_capped_time_to_correct_localisation"] == 6


def test_late_correct_response_is_timeout():
    p, a, r = fixture()
    r[0]["elapsed_seconds"] = 10.01
    row = score(p, a, r)["trials"][0]
    assert row["status"] == "timeout"
    assert row["exact_correct"] is False
    assert row["reported_nodes"] == []


def test_independent_units_not_ticks_define_paired_interval():
    p, a, r = fixture()
    result = score(p, a, r)
    assert result["paired"]["dashboard"]["units"] == 2
    assert result["paired"]["dashboard"]["pointwise_95pct_hoeffding_interval"] == [-1, 1]
    assert result["evidence_kind"] == "synthetic_smoke"


@pytest.mark.parametrize("mutation", [
    lambda p,a,r: r.append(copy.deepcopy(r[0])),
    lambda p,a,r: r[0].update(trial_id="unknown"),
    lambda p,a,r: r[0].update(detected_nodes=["A1", "A1"]),
    lambda p,a,r: r[0].update(detected_nodes=["Z9"]),
    lambda p,a,r: r[0].update(elapsed_seconds=float("nan")),
    lambda p,a,r: r[0].update(elapsed_seconds=True),
    lambda p,a,r: r[0].update(status="error"),
    lambda p,a,r: r[0].update(truth=["A1"]),
    lambda p,a,r: p["assignments"].append(copy.deepcopy(p["assignments"][0])),
    lambda p,a,r: p["assignments"][0].update(timeout_seconds=0),
    lambda p,a,r: p.update(assignments=[]),
    lambda p,a,r: a["cases"].update(extra=[]),
    lambda p,a,r: p["assignments"][0].update(unit_id="unpaired"),
])
def test_malformed_or_selected_trials_rejected(mutation):
    p, a, r = fixture()
    mutation(p, a, r)
    with pytest.raises(ValueError):
        score(p, a, r)


def test_undefined_class_rates_remain_null():
    p, a, r = fixture()
    a["cases"]["c1"] = []
    for response in r:
        response["detected_nodes"] = []
    output = score(p, a, r)["arms"]["wall"]
    assert output["fault_localisation_rate"] is None
    assert output["mean_capped_time_to_correct_localisation"] is None


def test_baseline_only_uses_observer_grids_and_strict_boundary():
    reference = {c: [80, 80, 80] for c in CELLS}
    observed = copy.deepcopy(reference)
    observed["A1"] = [105, 80, 80]
    case = dict(case_id="c1", reference_rgb=reference, observed_rgb=observed)
    assert baseline([case], 25)[0]["detected_nodes"] == []
    assert baseline([case], 24)[0]["detected_nodes"] == ["A1"]
    case["answer"] = ["B2"]
    with pytest.raises(ValueError):
        baseline([case], 25)


@pytest.mark.parametrize("bad", [float("inf"), float("nan"), True, -1, 256])
def test_baseline_rejects_malformed_rgb(bad):
    reference = {c: [80, 80, 80] for c in CELLS}
    observed = copy.deepcopy(reference)
    observed["A1"][0] = bad
    with pytest.raises(ValueError):
        baseline([dict(case_id="c1", reference_rgb=reference, observed_rgb=observed)], 25)


def test_demo_separates_answers_and_cli_hashes_inputs(tmp_path):
    demo(tmp_path / "demo")
    observer, evaluator = tmp_path / "demo/observer", tmp_path / "demo/evaluator"
    assert sorted(p.name for p in observer.iterdir()) == ["cases.json"]
    cases = json.loads((observer / "cases.json").read_text())
    assert all(set(c) == {"case_id", "reference_rgb", "observed_rgb"} for c in cases)
    argv = ["score", "--protocol", str(evaluator / "protocol.json"), "--answers",
            str(evaluator / "answers.json"), "--responses", str(evaluator / "responses.json"),
            "--out", str(tmp_path / "score.json")]
    assert main(argv) == 0
    out = json.loads((tmp_path / "score.json").read_text())
    assert out["result"]["evidence_kind"] == "synthetic_smoke"
    assert set(out["input_sha256"]) == {"protocol", "answers", "responses"}
    assert out["result"]["arms"]["reference"]["exact_accuracy"] == 1
    with pytest.raises(SystemExit) as e:
        main(argv)
    assert e.value.code == 2  # No silent overwrite of prior evidence.


def test_cli_rejects_bad_json_without_writing_result(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json}")
    with pytest.raises(SystemExit) as e:
        main(["baseline", "--cases", str(bad), "--threshold", "25", "--out", str(tmp_path / "result.json")])
    assert e.value.code == 2
    assert not (tmp_path / "result.json").exists()


def test_duplicate_json_object_keys_rejected(tmp_path):
    path = tmp_path / 'cases.json'
    path.write_text('[{"case_id":"one","case_id":"two"}]')
    with pytest.raises(SystemExit) as e:
        main(['baseline', '--cases', str(path), '--threshold', '25', '--out', str(tmp_path / 'out.json')])
    assert e.value.code == 2
    assert not (tmp_path / 'out.json').exists()


def test_enormous_integer_time_rejected():
    p, a, r = fixture()
    p['assignments'][0]['timeout_seconds'] = 10**1000
    with pytest.raises(ValueError):
        score(p, a, r)


def test_concurrent_output_creator_not_overwritten(tmp_path, monkeypatch):
    from pathlib import Path
    demo(tmp_path / 'demo')
    target = tmp_path / 'out.json'
    original_open = Path.open
    def concurrent_open(path, mode='r', *args, **kwargs):
        if path == target and mode == 'x':
            with original_open(path, 'w') as handle:
                handle.write('other writer')
        return original_open(path, mode, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', concurrent_open)
    with pytest.raises(SystemExit) as e:
        main(['baseline', '--cases', str(tmp_path / 'demo/observer/cases.json'),
              '--threshold', '25', '--out', str(target)])
    assert e.value.code == 2
    assert target.read_text() == 'other writer'
