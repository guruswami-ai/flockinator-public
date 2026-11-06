# Pre-registration: commitment strategy — confirmatory run

Declared before any confirmatory execution, following the exploratory
dev results in
[commitment-strategy-dev-results.md](commitment-strategy-dev-results.md)
(seeds 0–31), which must not be reused for confirmation.

## Design (unchanged from the dev simulator)

Simulator: `tools/kulira-core/kulira_core/commitment.py`, base
parameters exactly as pre-registered (16 nodes, 192 tiles, 12 sorties,
overlap 0.055, detection 0.85, hazard multiplier 1.0, near posture,
tactical launch threshold 30, recharge +25).

- **Seeds:** 1000–1127 inclusive (128 operations per policy). No seed
  may be added, dropped, or re-run with different parameters after
  results are seen; failures of the runner are reported, not replaced.
- **Policies (confirmatory set):** `escalate-4-16`,
  `target-8-rotate`, `fixed-14-hold` (the current 14+2 shape),
  `fixed-16-hold` (no reserve). `escalate-4-16-far` is carried as a
  clearly-labelled exploratory secondary only.

## Confirmatory hypotheses

- C1: `escalate-4-16` finds at least as often as `fixed-14-hold`
  (found-rate difference ≥ 0 within noise) with materially higher
  second-request readiness (difference ≥ +0.5 nodes).
- C2: `fixed-16-hold` does not beat `escalate-4-16` on found rate
  despite maximal coverage (battery-synchrony / overlap brittleness
  replicates beyond dev seeds).
- C3: `target-8-rotate` retains a better balanced profile than
  `fixed-14-hold`: found rate no worse, readiness no worse, with at
  least one strictly better beyond noise.

Noise yardstick: with n=128, the standard error of a found-rate
difference is at most ~0.06; differences below that are reported as
indistinguishable, not as wins. Metrics stay separate (found rate,
found-by-4, readiness, serviceable, damaged/lost, node-sorties); the
illustrative utility is quoted only with its formula.

## Out of scope

No planner or firmware change. A planner recommendation requires this
confirmatory result plus survivor-distance, daylight-cutoff and repair
variants under a further pre-registration.
