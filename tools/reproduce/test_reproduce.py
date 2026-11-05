"""Scientific invariants + canonical-output regression for the flagship benchmark."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("repro", Path(__file__).parent / "run.py")
run = importlib.util.module_from_spec(spec); spec.loader.exec_module(run)

def _content():
    return run.scientific_content()

def test_totals_and_ordering():
    c = _content(); p = c["pooled"]
    assert all(v["tasks"] == 2048 for v in p.values())
    assert p["clear"]["rate"] > p["private"]["rate"] > p["scrambled"]["rate"]

def test_canonical_matches_expected():
    import json
    expected = json.loads((Path(__file__).parent / "expected.json").read_text())
    assert expected["scientific_content"] == _content()

def test_per_seed_rows_complete():
    c = _content()
    assert [r["seed"] for r in c["per_seed"]] == list(range(16))
    assert all(r["clear_tasks"] == 128 for r in c["per_seed"])
