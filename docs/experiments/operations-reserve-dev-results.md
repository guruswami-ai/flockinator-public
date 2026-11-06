# Results (DEV): fleet commitment and reserve strategy

Status: **exploratory dev run, seeds 0-19** under
[operations-reserve-preregistration.md](operations-reserve-preregistration.md).
Evidence: `validation/kulira/operations-reserve-dev-001.json`.
Module: `tools/kulira-core/kulira_core/operations.py`
(tests: `test_operations.py`, 6 passed). Simulation only.

## Baseline results (4 incidents per daylight window)

| Strategy | Find rate | Mean turns to find | Ready at end | Ready battery | Damaged events | Lost | Unattempted |
|---|---|---|---|---|---|---|---|
| K1 launch 1 | 0.463 | 33.0 | 15.90 | 91.9 | 5 | 0 | 0 |
| K2 launch 2 | 0.813 | 28.7 | 15.95 | 89.8 | 6 | 0 | 0 |
| K4 launch 4 | 0.963 | 17.7 | 15.80 | 92.2 | 13 | 0 | 0 |
| K8 launch 8 | 0.988 | 10.2 | 15.60 | 94.1 | 14 | 0 | 0 |
| K8R launch 8, rotate | 0.988 | 10.2 | 15.60 | 93.4 | 14 | 0 | 0 |
| K14 park 2 (current) | 1.000 | 7.5 | 15.85 | 91.2 | 8 | 0 | 0 |
| K16 launch all | 1.000 | 5.7 | 15.70 | 93.9 | 14 | 0 | 0 |
| ESC 4 then +8 | 1.000 | 17.8 | 15.50 | 90.7 | 19 | 0 | 0 |

Pareto frontier (find rate vs ready at end): **K14 and K2**
(K2 is the low-commitment extreme: fewer finds, marginally most
aircraft left). K14 weakly dominates K16: same finds, slightly
more ready aircraft, at a cost of ~1.8 turns slower discovery.

## Hypotheses

- **H1 diminishing returns: supported.** The knee is at or below
  K4-K8. K16 beats K8 by only 1.25 points of find rate.
- **H2 strategic reserve: reserve is nearly free in this regime.**
  K14 matches K16 on finds and ends with at least as many ready
  aircraft. The feared mission-level cost of parking 2 does not
  appear at these parameters.
- **H3 escalation: passes the Pareto test, fails the clock.** ESC
  matches K14 finds and readiness, but is far slower to find
  (17.8 vs 7.5 turns) because the first wave is small, and it
  records the most damage events. For a survivor, time is the
  metric escalation sacrifices.
- **H4 rotation: no measurable effect.** K8R is identical to K8
  on finds and readiness; roster rotation neither helps nor hurts
  when recharge is this generous.

## The honest limitation

In the baseline regime, **nothing operational binds**: daylight
(240 turns) is never exhausted, recharge (+12/incident) refills
faster than missions drain, damage repairs in one missed incident,
and there are zero losses and zero unattempted incidents under
every strategy. Ready-at-end sits between 15.5 and 16.0 for all
eight strategies. The reserve question therefore cannot be settled
here - the simulator says the parked-2 rule is cheap, but partly
because the world is kind.

The sensitivity sweeps show where the question starts to bite:

- At `p_fail = 0.006` (3x mechanical failure), K14 ends with 15.35
  ready vs K16 14.95 and K8 14.90, with equal-or-better finds;
  small commitments collapse (K1 find rate 0.34).
- At `p_detect = 0.5`, the knee shifts right: K8 0.95, K14 0.99,
  K16 1.00 - commitment buys real discovery when sensing is poor.
- At 25% sweep overlap, K1 collapses (0.29) while K8+ stay at 1.00.
- Far-survivor fraction 0.35 changes little at baseline failure
  rates.

## Follow-up required (new pre-registration, not a retune)

A binding-regime variant: more incidents per window (8), slower
recharge (+4), shorter daylight (160 turns), and damage that can
ground aircraft for the rest of the window. Only there can
unattempted incidents, losses, and second-incident readiness
discriminate between parking 2, rotating 8, and launching all 16.
Until that run exists, the correct statement is: **at benign
parameters the strategic reserve costs nothing measurable; under
failure or poor sensing, larger commitment - including the current
14 - is favoured, and slow escalation trades away discovery time.**

## Planner follow-up (proposal to firmware/planner owner)

No planner or firmware change is proposed from this dev screen.
If the binding-regime run confirms a cost to parking 2, the
candidate change to evaluate - in the planner owner's own
pre-registration and canary process - is making the parked count
scenario-dependent (distance class and follow-up probability)
rather than fixed at 2. The tactical 3-point landing reserve is a
separate per-aircraft protection and is not challenged by these
results.
