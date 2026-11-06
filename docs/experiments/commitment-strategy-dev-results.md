# Commitment strategy - dev results (exploratory)

Status: exploratory dev run, seeds 0-31 (32 operations per policy),
declared in
[commitment-strategy-preregistration.md](commitment-strategy-preregistration.md)
before implementation. Evidence:
`validation/kulira/commitment-strategy-dev-001.json`. Simulator:
`tools/kulira-core/kulira_core/commitment.py`. This is a transparent
host policy simulator, not the Korvo planner, not firmware, and not
evidence about a physical aircraft.

With 32 seeds, the standard error of a found rate near 50% is about
0.09. Individual differences below roughly 0.18 are therefore not
decisive on their own; the patterns that survive the sensitivity
sweeps matter more than any single row.

## Base results (near posture)

| Policy | Found | By sortie 4 | Mean find sortie* | Coverage | Node-sorties | Damaged | Lost | Serviceable end | Readiness at 6/end | Utility** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fixed-1-hold | 0.094 | 0.094 | 2.33 | 0.092 | 5.91 | 0.16 | 0.00 | 15.84 | 15.81 | 7.43 |
| fixed-2-hold | 0.188 | 0.063 | 6.50 | 0.200 | 12.81 | 0.03 | 0.06 | 15.91 | 15.91 | 14.95 |
| fixed-4-hold | 0.281 | 0.094 | 5.44 | 0.313 | 23.88 | 0.16 | 0.06 | 15.78 | 15.41 | 21.19 |
| fixed-8-hold | 0.469 | 0.125 | 6.67 | 0.474 | 44.75 | 0.28 | 0.25 | 15.47 | 14.88 | 32.84 |
| fixed-12-hold | 0.656 | 0.313 | 6.19 | 0.522 | 59.38 | 0.66 | 0.16 | 15.19 | 14.50 | 47.56 |
| fixed-14-hold (current 14+2 shape) | 0.594 | 0.219 | 6.58 | 0.583 | 72.94 | 0.97 | 0.25 | 14.78 | 14.31 | 36.23 |
| fixed-16-hold (no reserve) | 0.500 | 0.156 | 6.50 | 0.625 | 88.28 | 1.09 | 0.19 | 14.72 | 14.25 | 23.15 |
| target-8-rotate | 0.688 | 0.219 | 6.36 | 0.677 | 64.97 | 0.53 | 0.25 | 15.22 | 15.59 | 48.91 |
| target-14-rotate | 0.750 | 0.281 | 6.75 | 0.649 | 76.03 | 1.00 | 0.22 | 14.78 | 12.19 | 51.24 |
| escalate-4-16 | 0.719 | 0.125 | 6.48 | 0.633 | 64.28 | 0.47 | 0.22 | 15.31 | 15.22 | 52.65 |
| fixed-8-hold-far | 0.625 | 0.375 | 5.50 | 0.531 | 33.00 | 0.66 | 0.22 | 15.13 | 13.59 | 50.53 |
| target-14-rotate-far | 0.719 | 0.313 | 5.61 | 0.726 | 60.44 | 1.44 | 0.38 | 14.19 | 10.81 | 49.45 |
| escalate-4-16-far | 0.875 | 0.438 | 4.71 | 0.559 | 37.00 | 1.03 | 0.31 | 14.66 | 9.59 | 72.66 |

\* Found operations only. \** Illustrative only:
`found * 100 - 8 * lost - 3 * damaged - 0.25 * node_sorties`.
Do not quote utility without the separate metrics.

## What the dev run suggests

- **More launch is not monotonically better.** Coverage rises with
  commitment, but found rate does not: fixed-16 covers most yet finds
  less than fixed-12, target-14-rotate, and escalate-4-16 in this run.
  One mechanism is battery synchrony: a whole fleet launched together
  drains together, reaches the launch threshold together, and creates
  a fleet-wide recharge valley. Rotation and escalation stagger that
  valley.
- **Rotation beats a fixed cohort at the same target on search, with a
  readiness caveat.** target-8-rotate finds 0.688 vs fixed-8-hold
  0.469 and also ends readier (15.59 vs 14.88). At 14, rotation finds
  more (0.750 vs 0.594) but spends the rested nodes too, so readiness
  at sortie 6 falls (12.19 vs 14.31). Rotation is not a free reserve;
  it converts reserve battery into search.
- **Escalation is the balanced-profile candidate.** escalate-4-16
  nearly matches the best near search (0.719 vs 0.750) while keeping
  the best readiness among effective policies (15.22) and the fewest
  damaged nodes of the large policies. Its weakness is urgency: only
  0.125 found by sortie 4, because it starts small on purpose.
- **Far posture buys speed with readiness.** escalate-4-16-far is the
  fastest and most successful search here (0.875, mean find sortie
  4.71) and the least ready for a second request (9.59). That is a
  declared trade, not a defect: it suits a life-first profile and
  should never be the silent default.
- **The current fixed 14+2 shape is not supported as a universal
  default.** fixed-14-hold is beaten on search by rotation and
  escalation at similar or lower cost, and its two parked nodes do not
  even buy the best readiness, because the committed fourteen still
  drain in lockstep. The number "2 in reserve" is answering the wrong
  question; the policy over time is the decision.

## Hypotheses, scored against the pre-registration

- H1 (diminishing returns): partly supported, but the curve is
  non-monotonic at the top end under base parameters; battery
  synchrony and seed noise are confounded with overlap waste.
- H2 (target-14-rotate keeps search and improves readiness): search
  part supported, readiness part **falsified** at sortie 6.
- H3 (rotation dominates hold): supported at target 8; at target 14
  it is a search-for-readiness trade, not dominance.
- H4 (escalation balances): supported for the balanced profile;
  falsified for the urgent profile (slow early finds by design).
- H5 (far trades readiness): supported. The size of the search gain
  is policy-dependent (large for escalation and fixed-8, absent for
  target-14 in this run).

## Sensitivity (found rate / readiness at 6/end)

- Overlap 0: fixed-14-hold 0.906/11.25, fixed-16 0.875/8.03,
  escalate 0.875/15.00. Overlap 0.11: fixed-16 collapses to
  0.188/13.53 while escalate holds 0.594/14.75. **High commitment is
  brittle exactly when coordination waste is high** - the ranking is
  parameter-dependent and must not be quoted without the overlap
  assumption.
- Detection 0.70 -> 0.95 scales every policy; escalate and
  target-14-rotate stay at or near the top at all three levels.
- Hazard 2x: target-14-rotate falls to 0.594/11.06 readiness and
  13.56 serviceable; escalate retains 0.688/13.84 and 14.28
  serviceable. Escalation's advantage grows as attrition rises.

## Recommendations (proposals to the planner owner, not firmware changes)

1. Replace the fixed reserve count with an explicit commitment policy
   selected by declared objective profile (urgent / balanced /
   fleet-preserving) before launch.
2. Treat escalate-on-no-find as the balanced default candidate and
   rotation as the mechanism that prevents battery-synchrony valleys;
   keep the tactical landing reserve as a separate per-node rule.
3. Require any far/all-out choice to state the second-request
   readiness it is spending, in the mission record.
4. Before any planner change: a confirmatory run on fresh seeds
   (to be declared before running) comparing escalate-4-16,
   target-8-rotate, fixed-14-hold, and fixed-16-hold, plus variants
   for survivor distance, daylight cutoff, and repair. Dev seeds
   0-31 must not be reused for confirmation.

## Long-horizon note

Nothing here optimises a fleet across days. Repair queues,
replacements, retained trust/reputation state, and fleet growth turn
today's readiness metric into tomorrow's starting condition. That is
the operational level at which "explore versus stay with the school"
risk thresholds should eventually be learned - against a declared
objective, with survival of capability as a constraint, not as a
single-mission afterthought.
