import json, subprocess, sys
from pathlib import Path
from kulira_core.e2e import build_run

def test_e2e_run_scores_with_fleet_scorer(tmp_path):
    out = build_run(tmp_path/"run", seed=42)
    assert (out/"director.json").exists()
    scorer = Path(__file__).resolve().parents[2] / "tools/fleet-score/score.py"
    r = subprocess.run([sys.executable, str(scorer), str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    score = json.loads(r.stdout)
    # Kulira's false Enemy->Friendly sighting is hearsay-amplified but only
    # one direct sighting exists, so it must not commit at >=3
    assert score["reports_by_auth_status"]["hearsay_relayed"] >= 1
    assert score["reports_by_auth_status"]["direct_verified"] >= 1
