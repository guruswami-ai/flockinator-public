# Feedback-trust evidence status and remaining acceptance gaps

**2026-11-07; source reviewed at `5f102de`.** This reconciles
[#134](https://github.com/guruswami-ai/flockinator-public/issues/134) with the
shipped evidence. It does not alter historical registrations, outputs or criteria.

| Requested evidence | Current public artifact | What remains |
|---|---|---|
| Separate delayed/incomplete runner | [`feedback_trust.py`](../../tools/kulira-core/kulira_core/feedback_trust.py) and [registration](feedback-trust-preregistration.md) | Runner has no explicit version field; pin its Git revision when reproducing |
| Truth-access boundary and full-feedback compatibility | [`test_feedback_trust.py`](../../tools/kulira-core/test_feedback_trust.py): future/unrevealed truth, exact reveal boundary, positive learning sensitivity, compatibility and probation tests | These verify the tested simulator boundary, not a deployed information boundary |
| Frozen primary contrasts and complete cells | [Dev registration/results](feedback-trust-results.md), [confirmatory registration](feedback-trust-confirmatory-preregistration.md), [confirmatory results](feedback-trust-confirmatory-results.md); JSONs below | Published point rules stand; later uncertainty must be labelled post hoc |
| Paired outcomes and coverage | [`feedback-trust-paired-001.json`](../../validation/kulira/feedback-trust-paired-001.json), same-window corrections in confirmatory results | Historical `decisions`/`recall` fields cover the whole sequence; `dangerous_second` covers contacts 30–59. Do not combine them as if windows matched |
| Learning attribution | [Frozen diagnostic](../../validation/kulira/feedback-trust-frozen-001.json) and dated corrections | Diagnostic is post hoc on exposed seeds; a controlled confirmatory learning effect still needs [matched controls](feedback-trust-matched-control-proposal.md) |
| Update cost and equal information budget | Separate reveal stream and retained decision logs in runner | No complete published per-cell applied-update counts or timing/cost table; future frozen controls must receive the same reveals |
| Research/literature audit | [Contributor audit](../research/contributor-notes/feedback-trust-audit.md) | Audit is explicitly not adopted and its ideal matched controls were not the historical E comparison. It contains no cited primary-literature review; do not claim that work complete |

The development JSON has all 27 policy × delay × availability cells; the
confirmatory JSON has all 12 registered cells. The selected table in the prose
is not the full grid. The original point-rule verdicts are distinct from
population uncertainty and from the later causal interpretation.

The supported conclusion is bounded: at full feedback REP has fewer dangerous
commits than E; at the sparse/delayed cell its dangerous count is slightly
higher, with more survivor finds. E and REP use different thresholds. The
post hoc matched diagnostic shows updating reduces dangerous commits relative
to frozen REP, so the historical E comparison cannot justify "learning is
actively misleading". REP-P's extreme-cell equality with frozen unit weights
is a scoped result, not a general equivalence theorem. See the dated result
corrections for the exact cells and window labels.

## Reproduction and closure

From the repository root, the existing boundary/compatibility tests run with:

```sh
uv run --project tools/kulira-core --locked pytest tools/kulira-core/test_feedback_trust.py
```

All 27 development and 12 confirmatory cells reproduced exactly at the reviewed
source. This command verifies the **already exposed** seeds without writing
over an artifact:

```sh
PYTHONPATH=tools/kulira-core uv run --no-project python - <<'PY'
import json
from pathlib import Path
from kulira_core.feedback_trust import run_feedback

for split, seeds, delays, avails in (
    ("dev", range(220, 240), (0, 5, 15), (1.0, 0.5, 0.25)),
    ("confirmatory", range(240, 260), (0, 15), (1.0, 0.25)),
):
    path = Path(f"validation/kulira/feedback-trust-{split}-001.json")
    expected = json.loads(path.read_text())["results"]
    actual = run_feedback(seeds, delays=delays, avails=avails)
    if actual != expected:
        raise SystemExit(f"{split}: reproduction mismatch")
    print(f"{split}: {len(actual)} cells match")
PY
```

The JSONs are summaries, not self-contained per-seed journals; retain
generator/runner revision and arguments beside any reproduction. Re-executing
historical seeds is verification, not a fresh confirmatory study.

#134 has substantial implementation and results, but its broad acceptance is
not fully satisfied: same-window complete reporting, update-cost evidence,
primary-literature context and matched-threshold causal attribution need
explicit disposition. A maintainer can close the *historical bounded comparison*
with these limits and transfer the causal follow-up to #172; do not mark the
stronger original research question fully resolved merely because tests pass.
No new study or collection is authorized by this status note.
