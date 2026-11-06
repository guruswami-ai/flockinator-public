# Commitment strategy — confirmatory results

Status: confirmatory run executed exactly as declared in
[commitment-strategy-confirmatory-preregistration.md](commitment-strategy-confirmatory-preregistration.md):
seeds 1000–1127 (128 operations per policy), base parameters unchanged,
no seed added, dropped, or re-run. Evidence:
`validation/kulira/commitment-strategy-confirmatory-001.json`.
Exploratory context: `commitment-strategy-dev-results.md` (seeds 0–31).

## Results

| Policy | Found | By sortie 4 | Mean find sortie* | Coverage | Node-sorties | Damaged | Lost | Serviceable end | Readiness at 6/end | Utility** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| escalate-4-16 | 0.734 | 0.266 | 6.35 | 0.605 | 60.4 | 0.74 | 0.21 | 15.05 | 14.88 | 54.42 |
| target-8-rotate | 0.844 | 0.313 | 6.26 | 0.595 | 57.0 | 0.72 | 0.25 | 15.03 | 15.34 | 65.98 |
| fixed-14-hold (current 14+2 shape) | 0.602 | 0.297 | 5.22 | 0.538 | 67.7 | 0.73 | 0.39 | 14.88 | 12.80 | 37.91 |
| fixed-16-hold (no reserve) | 0.656 | 0.320 | 5.18 | 0.530 | 74.9 | 0.81 | 0.38 | 14.81 | 12.37 | 41.46 |
| escalate-4-16-far (exploratory) | 0.867 | 0.344 | 5.30 | 0.621 | 41.1 | 1.12 | 0.42 | 14.46 | 8.70 | 69.72 |

\* Found operations only. \** Illustrative only:
`found * 100 - 8 * lost - 3 * damaged - 0.25 * node_sorties`.

Paired per-seed differences (mean ± paired SE):

- escalate-4-16 − fixed-14-hold: found **+0.133 ± 0.061**,
  readiness **+2.08 ± 0.49** nodes.
- fixed-16-hold − escalate-4-16: found **−0.078 ± 0.057**.
- target-8-rotate − fixed-14-hold: found **+0.242 ± 0.055**,
  readiness **+2.54 ± 0.47** nodes.

## Hypotheses, scored

- **C1 (escalation ≥ fixed-14 on search, better readiness): CONFIRMED.**
  Escalation finds more (+0.133, ~2.2 paired SE) and ends with about
  two more launch-ready nodes. The dev-run pattern replicates on
  fresh seeds.
- **C2 (all-out does not beat escalation): SUPPORTED, not decisive
  alone.** Fixed-16 finds less than escalation (−0.078 ± 0.057,
  ~1.4 SE) despite maximal commitment, consistent with the dev run
  and with the overlap sensitivity sweep where fixed-16 collapses.
  Three independent seed sets now point the same way; no seed set
  shows all-out winning on the balanced profile.
- **C3 (target-8-rotate balanced-dominates fixed-14): CONFIRMED,
  strongly.** Rotating eight finds +0.242 more often with +2.54
  readiness — the single clearest result in the series. Committing
  *fewer* nodes, but rotating them, beats parking two and draining
  fourteen in lockstep on both axes at once.

## What this establishes, and what it does not

Established (within this transparent simulator): the fixed 14+2
commitment shape is dominated at operation level. Rotation is the
mechanism that matters most (it prevents fleet-wide battery-synchrony
valleys), escalation is a robust second, and far posture remains a
declared life-first trade (best search, worst readiness 8.70).

Not established: anything about the physical fleet, the Korvo
planner's route geometry, survivor-distance distributions, daylight
cutoffs, or repair/replacement over multiple days. Those need their
own pre-registered variants before any planner recommendation is
acted on. This result is a reason to test rotation/escalation in the
planner's own simulator — not a reason to change flight behaviour
directly.

## Recommendation carried forward (proposal to the planner owner)

1. Add commitment policy (hold / rotate / escalate) as an explicit,
   logged mission parameter in the planner's simulator, defaulting
   to the current behaviour for comparability.
2. Pre-register planner-level variants (survivor distance, daylight
   cutoff, repair) comparing fixed-14 against target-8-rotate and
   escalate-4-16 on the planner's own coverage model.
3. Keep the tactical per-node landing reserve separate and unchanged;
   nothing here argues against it.
