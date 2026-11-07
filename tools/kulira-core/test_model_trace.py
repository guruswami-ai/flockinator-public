import copy
import json
from pathlib import Path

import pytest

from kulira_core import model_trace as trace


def request():
    grid = {cell: [80, 80, 80] for cell in trace.CELLS}
    observed = copy.deepcopy(grid)
    observed["A1"] = [160, 80, 80]
    return trace.fault_request("trial-001", "requested-model", {"temperature": 0},
                               {"case_id": "case-001", "reference_rgb": grid,
                                "observed_rgb": observed})


def response(**updates):
    value = {"status": "completed", "detected_nodes": ["A1"],
             "reported_model": "reported-model", "usage": {"input_tokens": 12, "output_tokens": 3},
             "cost_usd": None, "cost_source": None, "error_code": None}
    value.update(updates)
    return value


def test_start_is_durable_before_single_call_and_request_is_immutable(tmp_path):
    directory = tmp_path / "attempt"
    supplied = request()
    before = copy.deepcopy(supplied)
    calls = []
    def invoke(text):
        calls.append(text)
        assert isinstance(text, str)
        assert trace.verify(directory)["status"] == "INCOMPLETE"
        assert text.encode() == (directory / "request.json").read_bytes()
        # The caller's mutable object is not the transmitted snapshot.
        supplied["parameters"]["temperature"] = 2
        assert json.loads(text) == before
        return response()
    result = trace.run_attempt(directory, supplied, invoke, evidence_kind="synthetic_test")
    assert len(calls) == 1
    assert result["status"] == "COMPLETED"
    assert result["requested_model"] == "requested-model"
    assert result["response"]["reported_model"] == "reported-model"
    assert json.loads((directory / "request.json").read_text()) == before
    assert result["response"]["cost_usd"] is None
    assert result["elapsed_seconds"] >= 0


def test_builder_snapshots_input_structures():
    original = request()
    built = trace.fault_request(original["trial_id"], original["requested_model"],
                                original["parameters"], original["case"])
    original["case"]["observed_rgb"]["A1"][0] = 0
    assert built["case"]["observed_rgb"]["A1"][0] == 160


def test_invoke_exception_records_no_message_or_credentials(tmp_path):
    marker = "DO_NOT_ARCHIVE_exception_secret"
    calls = []
    def fail(_):
        calls.append(1)
        raise RuntimeError(marker)
    result = trace.run_attempt(tmp_path / "attempt", request(), fail, evidence_kind="synthetic_test")
    assert len(calls) == 1
    assert result["status"] == "ERROR"
    assert result["response"]["error_code"] == "invoke_exception"
    assert result["response"]["usage"] is None
    assert result["response"]["cost_usd"] is None
    assert marker not in "".join(p.read_text() for p in (tmp_path / "attempt").iterdir())


def test_reported_failure_preserves_available_usage_cost(tmp_path):
    reply = response(status="error", detected_nodes=[], error_code="provider_error",
                     cost_usd=.01, cost_source="provider_reported")
    result = trace.run_attempt(tmp_path / "attempt", request(), lambda _: reply,
                               evidence_kind="synthetic_test")
    assert result["status"] == "ERROR"
    assert result["response"]["usage"]["input_tokens"] == 12
    assert result["response"]["cost_usd"] == .01


def test_interrupt_retains_incomplete_start(tmp_path):
    def interrupt(_):
        raise KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        trace.run_attempt(tmp_path / "attempt", request(), interrupt, evidence_kind="synthetic_test")
    assert trace.verify(tmp_path / "attempt")["status"] == "INCOMPLETE"
    assert trace.main([str(tmp_path / "attempt")]) == 2


def test_latency_uses_monotonic_not_wall_clock(tmp_path, monkeypatch):
    clocks = iter([100, 102.5])
    stamps = iter(["2026-11-07T10:00:00+00:00", "2026-11-07T09:00:00+00:00"])
    monkeypatch.setattr(trace.time, "monotonic", lambda: next(clocks))
    monkeypatch.setattr(trace, "_utc", lambda: next(stamps))
    result = trace.run_attempt(tmp_path / "attempt", request(), lambda _: response(),
                               evidence_kind="synthetic_test")
    assert result["elapsed_seconds"] == 2.5


@pytest.mark.parametrize("mutation", [
    lambda r: r.update(authorization="secret"),
    lambda r: r["parameters"].update(api_key="secret"),
    lambda r: r["case"].update(truth=["A1"]),
    lambda r: r.update(instruction="arbitrary private text"),
    lambda r: r["parameters"].update(top_p=2),
    lambda r: r["parameters"].update(temperature=float("nan")),
    lambda r: r["parameters"].update(max_output_tokens=0),
    lambda r: r["parameters"].update(seed=True),
    lambda r: r["parameters"].update(seed=10**1000),
    lambda r: r["case"]["observed_rgb"].update(A1=[256, 0, 0]),
])
def test_request_rejected_before_directory_or_invocation(tmp_path, mutation):
    value = request()
    mutation(value)
    with pytest.raises(ValueError):
        trace.run_attempt(tmp_path / "attempt", value, lambda _: pytest.fail("called"),
                          evidence_kind="synthetic_test")
    assert not (tmp_path / "attempt").exists()


@pytest.mark.parametrize("mutation", [
    lambda r: r.update(headers={"authorization": "DO_NOT_ARCHIVE"}),
    lambda r: r.update(error_text="DO_NOT_ARCHIVE"),
    lambda r: r.update(detected_nodes=["A1", "A1"]),
    lambda r: r.update(detected_nodes=["Z9"]),
    lambda r: r.update(status="error", error_code="bad", detected_nodes=[]),
    lambda r: r.update(cost_usd=float("inf"), cost_source="provider_reported"),
    lambda r: r.update(cost_usd=1, cost_source=None),
    lambda r: r.update(cost_usd=None, cost_source="adapter_estimated"),
    lambda r: r.update(usage={"input_tokens": True, "output_tokens": 0}),
])
def test_invalid_responses_still_leave_bounded_failed_attempt(tmp_path, mutation):
    reply = response()
    mutation(reply)
    result = trace.run_attempt(tmp_path / "attempt", request(), lambda _: reply,
                               evidence_kind="synthetic_test")
    assert result["status"] == "ERROR"
    assert result["response"]["error_code"] == "invalid_response"
    assert "DO_NOT_ARCHIVE" not in (tmp_path / "attempt/outcome.json").read_text()


def test_existing_directory_is_never_reused_or_called(tmp_path):
    directory = tmp_path / "attempt"
    trace.run_attempt(directory, request(), lambda _: response(), evidence_kind="synthetic_test")
    original = {p.name: p.read_bytes() for p in directory.iterdir()}
    with pytest.raises(FileExistsError):
        trace.run_attempt(directory, request(), lambda _: pytest.fail("called"),
                          evidence_kind="synthetic_test")
    assert {p.name: p.read_bytes() for p in directory.iterdir()} == original


def test_concurrent_outcome_file_is_not_overwritten(tmp_path):
    directory = tmp_path / "attempt"
    def race(_):
        (directory / "outcome.json").write_text("other-writer")
        return response()
    with pytest.raises(FileExistsError):
        trace.run_attempt(directory, request(), race, evidence_kind="synthetic_test")
    assert (directory / "outcome.json").read_text() == "other-writer"
    with pytest.raises(ValueError):
        trace.verify(directory)


def test_trace_binding_rejects_swapped_and_tampered_inputs(tmp_path):
    directory = tmp_path / "attempt"
    trace.run_attempt(directory, request(), lambda _: response(), evidence_kind="synthetic_test")
    original = {p.name: p.read_bytes() for p in directory.iterdir()}
    for name, field, value in (("request.json", "trial_id", "trial-swapped"),
                               ("start.json", "evidence_kind", "observed"),
                               ("outcome.json", "start_sha256", "0" * 64)):
        record = json.loads(original[name]);record[field] = value
        (directory / name).write_text(json.dumps(record))
        with pytest.raises(ValueError):
            trace.verify(directory)
        (directory / name).write_bytes(original[name])
    assert trace.verify(directory)["status"] == "COMPLETED"


def test_verifier_rejects_extra_files_symlinks_and_duplicate_json_keys(tmp_path):
    directory = tmp_path / "attempt"
    trace.run_attempt(directory, request(), lambda _: response(), evidence_kind="synthetic_test")
    outcome = directory / "outcome.json"
    original = outcome.read_bytes()
    (directory / "raw-headers.json").write_text("{}")
    with pytest.raises(ValueError):
        trace.verify(directory)
    (directory / "raw-headers.json").unlink()
    outcome.unlink()
    (tmp_path / "external.json").write_bytes(original)
    outcome.symlink_to(tmp_path / "external.json")
    with pytest.raises(ValueError):
        trace.verify(directory)
    outcome.unlink()
    outcome.write_bytes(b'{"schema":"duplicated",' + original[1:])
    with pytest.raises(ValueError, match="duplicate"):
        trace.verify(directory)


def test_cli_success_failure_and_invalid_trace(tmp_path):
    good, failed = tmp_path / "good", tmp_path / "failed"
    trace.run_attempt(good, request(), lambda _: response(), evidence_kind="synthetic_test")
    trace.run_attempt(failed, request(), lambda _: None, evidence_kind="synthetic_test")
    assert trace.main([str(good)]) == 0
    assert trace.main([str(failed)]) == 2
    with pytest.raises(SystemExit) as exc:
        trace.main([str(tmp_path / "missing")])
    assert exc.value.code == 3
