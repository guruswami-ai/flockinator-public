# Pre-registration: binding-regime commitment and reserve

Status: **pre-registered before this variant was run.** Simulation
only. Follows [operations-reserve-preregistration.md](operations-reserve-preregistration.md);
the dev screen there was non-binding (no losses, no unattempted
incidents under any strategy), so this variant tightens the regime
as a new experiment - it is not a retune of the dev results, which
stand as published on seeds 0-19.

## Regime changes (the only changes)

- Incidents per window: 8 (was 4)
- Daylight: 160 turns (was 240)
- Inter-incident recharge: +4 (was +12)
- Damage grounds an aircraft for the **rest of the window**
  (was: miss one incident)
- All other simulator parameters frozen at baseline values
  (`p_detect 0.7`, `p_fail 0.002`, far fraction 0.15, no overlap)

## Strategies

Primary comparison: **K14** (park 2, current), **K8R** (launch 8,
rotate), **K16** (launch all), **ESC** (4, escalate +8 at turn 20).
K8 (fixed roster) is included as the rotation control for K8R.

## Primary metrics

Aircraft **lost**, **unattempted** incidents, and **second-incident
readiness** (ready count before incident 2; readiness before
incident 5 reported secondarily). Find rate, turns-to-find, ready
at end, damaged events are secondary. Report per strategy as
means over seeds; Pareto pair remains (finds, ready at end) with
losses as a third axis.

## Hypotheses and falsification

- **HB1 (regime binds):** at least one strategy records >0 mean
  unattempted incidents or >0 losses across the split. Falsified
  if the regime still does not bind - then the simulator, not the
  strategies, is revised in a further pre-registration.
- **HB2 (reserve protects the operation):** K14 has fewer lost +
  unattempted than K16, at a find-rate cost of <=5 points.
  Falsified if K16 matches K14 on lost + unattempted (reserve
  buys nothing even when the regime binds), or if K14's find
  cost exceeds 10 points (reserve too expensive).
- **HB3 (rotation preserves readiness):** K8R has >= K8
  second-incident readiness and >= K8 finds, with fewer lost.
  Falsified on any failure.
- **HB4 (escalation under binding):** ESC has the fewest lost +
  unattempted but the worst turns-to-find. Falsified if ESC is
  dominated on both axes by any single strategy.

## Seeds

Seeds **20-39**, frozen here before the run (the dev screen used
0-19; these are new to this experiment but design-exposed in the
wider programme - reported as such, no holdout claim).

## Follow-up rule

As before: findings are a proposal to the firmware/planner owner.
No planner, firmware, parked-count, or threshold change is made
from this repository side.
