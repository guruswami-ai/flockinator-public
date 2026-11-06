# Pre-registration: fleet commitment and reserve strategy (mission vs operational optimisation)

Status: **pre-registered before the simulator was run.** Simulation
only: no hardware, no radio, no on-node inference. Frozen parameters
below; any deviation is reported as a deviation.

## Why this experiment exists

Current fleet logic embeds two different reserves that were never
tested against each other:

- **Tactical reserve** — per-aircraft energy kept back for return and
  landing (Korvo planner: 3 points). This protects one aircraft on
  one sortie.
- **Strategic reserve** — fleet-level capability kept back for the
  next incident. The shared recon model currently parks exactly 2 of
  16 aircraft (`reserve` and `reserve+8`) on every mission, regardless
  of scenario, distance, or what may happen later.

Parking 2 of 16 was a commander's assumption, not a measured optimum.
A single aircraft may find the survivor; all 16 may find them faster
but arrive at the next incident damaged, flat, or absent. This
experiment separates the two questions:

- **Mission-level:** given one incident, how does the number
  committed affect probability and time of discovery?
- **Operational-level:** over a sequence of incidents inside one
  daylight window, how does commitment affect the fleet that remains
  — ready aircraft, energy, damage, losses, and readiness for a
  follow-up incident?

## Objective profiles (declared per scenario, never blended silently)

- **Life-first:** maximise survivors found; residual fleet is a
  secondary report, not a constraint.
- **Balanced:** survivors found and end-of-window ready fleet both
  reported as a Pareto pair; no single scalar winner.
- **Fleet-preserving:** maximise survivors found subject to ending
  the window with at least 8 airworthy aircraft.

The primary output is the **Pareto set** (survivors found vs ready
aircraft remaining, with losses as a third reported axis). Weighted
profile scores are secondary and must not be used to hide a
dominated strategy.

## Simulator (transparent, seeded, stdlib only)

Module: `tools/kulira-core/kulira_core/operations.py`.

- Fleet of 16 aircraft. Each has battery 0-100, state
  ready/airborne/damaged/lost, and a repair clock.
- An operation is up to 4 sequential incidents inside a daylight
  budget of 240 turns. Between incidents, ready aircraft recharge
  +12 battery (cap 100); damaged aircraft miss exactly one incident
  (repair), then return at 60 battery; lost aircraft never return.
- Each incident places one survivor in a search area of 576 cells.
  Survivor distance class: near (55%), mid (30%), far (15%). The
  class sets return distance and therefore reserve exposure.
- Per turn, each airborne aircraft sweeps 6 new cells (partitioned,
  no overlap in the baseline; overlap is a swept sensitivity). If
  the survivor's cell is swept, detection succeeds with
  `p_detect = 0.7` per pass.
- Energy: airborne drain 1.1/turn, plus distance surcharge on return
  (near 4, mid 8, far 14). An aircraft that would land below the
  15-point tactical reserve instead makes a forced landing: damaged
  with probability 0.5, lost with probability 0.1, otherwise safe
  but empty. Independent mechanical failure: `p_fail = 0.002` per
  airborne turn -> damaged.
- An incident ends when the survivor is found, when all airborne
  aircraft must return (energy), or when daylight ends the window.
  Later incidents in the window are then attempted with whatever
  fleet remains; an incident with zero ready aircraft is recorded
  as **unattempted**, which is an operational failure, not a
  mission failure.

## Strategies compared (commitment policies)

| ID | Policy |
|---|---|
| K1 | Launch 1 |
| K2 | Launch 2 |
| K4 | Launch 4 |
| K8 | Launch 8, fixed roster |
| K8R | Launch 8, rotate roster between incidents (rest = recharge priority) |
| K14 | Launch 14, park 2 (current fleet behaviour) |
| K16 | Launch all 16 |
| ESC | Launch 4; if not found by turn 20, escalate +8 from reserve |

Aircraft selection picks highest-battery ready aircraft except K8R,
which picks least-recently-flown first.

## Metrics (per operation, then mean over seeds)

- survivors found (of incidents that occurred), unattempted incidents
- mean turns to find (found incidents only)
- ready aircraft at window end; mean battery of ready aircraft
- damaged-events, aircraft lost
- second-incident readiness: ready count immediately before incident 2

## Hypotheses and falsification

- **H1 (diminishing returns):** find probability rises with k but
  with a knee at or below 8. Falsified if K16 finds >=10 points more
  survivors (percentage of incidents) than K8 on dev seeds.
- **H2 (strategic reserve pays operationally, costs at mission
  level):** K14 finds fewer survivors on incident 1 than K16 but
  ends the window with more ready aircraft and fewer unattempted
  incidents. Falsified if K14 is dominated by K16 on both axes (no
  operational benefit for the mission cost), or if K14 matches K16
  on finds *and* readiness (reserve is free - also a publishable
  result).
- **H3 (escalation captures most of both):** ESC is on or near the
  Pareto frontier - finds within 5 points of K14 with ready-at-end
  within 1 aircraft of K14. Falsified otherwise.
- **H4 (rotation is free readiness):** K8R ends with >= K8 ready
  aircraft and no fewer finds. Falsified if either fails.

## Sensitivity sweeps (reported, not tuned away)

`p_detect in {0.5, 0.7, 0.9}`, `p_fail in {0, 0.002, 0.006}`,
far-survivor fraction in {0.15, 0.35}, sweep overlap in {0, 0.25}.
If strategy ranking flips inside these ranges, the ranking is
reported as parameter-dependent, not resolved.

## Seeds

Dev seeds 0-19 (seed = one independent operation window). No
holdout claim: this is a dev-stage strategy screen. A confirmatory
run requires fresh seeds frozen after this screen, and any planner
or firmware change is Drishdi-owned and proposed, not made here.

## Planner follow-up rule

Findings are reported to the firmware/planner owner as a proposal
with the Pareto table. No change to the parked-2 rule, the planner
reserve, or thresholds is made from this repository side.
