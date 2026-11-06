# Pre-registration: commitment strategy - how many nodes to launch, and what to preserve

Status: pre-registered before implementation. Exploratory dev seeds
0-31 are declared here; any confirmatory seed set must be declared
before it is run and must not reuse 0-31.

## Why this experiment exists

The shared recon display model currently parks exactly two of its
sixteen nodes in every cycle: `reserve = hash(seed, cycle, 77) % 16`,
plus `(reserve + 8) % 16` (shared recon model). The other fourteen are
the only nodes allowed observations. That is a scheduling assumption
inherited from the original scouting framing. It has never been tested
as a search-and-rescue strategy.

Two different reserves must not be conflated:

1. **Tactical energy reserve** - whether one returning node has enough
   energy left to land safely. The survey planner already models a
   version of this (a landing reserve in its route scoring).
2. **Strategic capability reserve** - whether the fleet retains useful
   capability for the remainder of an operation and later requests.

This experiment tests the second. It treats fleet commitment as a
policy over time, `policy(state) -> active set`, not a fixed number
chosen once.

## Operational question

A rescue operation may be longer than one flight. Finding a survivor
quickly matters, but daylight, battery, mechanical failure, damage,
and failure to return consume the same fleet that later flights and
later requests need. A strategy that is best for the first flight can
therefore be poor for the operation.

Each scenario must state its high-level objective before launch. This
pre-registration separates three profiles and never merges them into
an unstated score:

- **Urgent search:** maximise probability of finding the survivor
  early, especially within the first four flights.
- **Balanced operation:** find the survivor within the operation while
  retaining a useful fleet for another request.
- **Fleet preservation:** retain maximum serviceable capability, while
  reporting the search cost openly rather than hiding it.

## Transparent simulator

This is a deliberately small policy simulator. It is not the Korvo
planner, not firmware, and not evidence about a physical aircraft.

- Sixteen nodes; 192 search tiles; one survivor on a uniformly random
  tile; twelve 15-minute sorties (180 minutes) or until found.
- On each sortie the policy selects an active set. A node may launch
  only if serviceable and battery is at least 30 (its tactical return
  threshold in this model).
- Every active node nominally searches three new tiles. Imperfect
  coordination makes total unique coverage
  `round(active * 3 * exp(-0.055 * (active - 1)))`, sampled from
  unsearched tiles (or all tiles if fewer remain). The exponential term
  is an overlap assumption to be sensitivity-tested, not a measured
  physical constant.
- If the survivor tile is among the uniquely searched tiles on that
  sortie, detection succeeds with probability 0.85.
- Near posture is the baseline. Far posture searches 50% more nominal
  tiles, costs 45 rather than 30 battery, and doubles both damage and
  loss hazards. Far is a secondary factor, tested only where declared.
- Flying costs 30 battery (near) or 45 (far). Nodes not launched
  recharge +25, capped at 100. Starting battery is 100.
- Per launched node per sortie: damage probability 0.012 and loss
  probability 0.004 (near); both doubled far. Damaged and lost nodes
  are unavailable for the rest of the operation. Repair and replacement
  are outside this one-operation model.
- A second request is assessed at the end of sortie 6, or at early
  termination if the survivor is found sooner: readiness is the number
  of serviceable nodes with battery at least 30 at that moment. It is a
  readiness measure only; the second request is not flown here.

## Policies

- `fixed-k-hold` for k = 1, 2, 4, 8, 12, 14, 16: a committed cohort of
  up to k nodes; nodes outside the cohort never launch in this
  operation. At k = 16 there is no held reserve.
- `target-k-rotate` for k = 8 and 14: maintain up to k active each
  sortie by choosing the highest-battery serviceable nodes, so rested
  nodes replace depleted nodes.
- `escalate-4-16`: begin at target 4; after each two unsuccessful
  sorties, increase target by 4 up to 16, choosing highest-battery
  serviceable nodes.
- Posture comparison (near vs far) only for fixed-8-hold,
  target-14-rotate, and escalate-4-16.

## Metrics (reported separately)

- Found probability by sorties 4 and 12; mean and median find sortie
  among found operations; coverage fraction; launched node-sorties.
- Nodes damaged, nodes lost, serviceable nodes remaining, mean battery
  among serviceable nodes, and second-request readiness after sortie 6
  (or early termination).
- Illustrative operation utility, printed only with its formula:
  `found * 100 - 8 * lost - 3 * damaged - 0.25 * node_sorties`.
  The Pareto table is primary; utility must not be quoted without
  the formula and the separate metrics.

## Hypotheses and falsification

- H1: found probability rises with active count but with diminishing
  returns. Falsified if fixed-14 and fixed-8 are within seed noise
  while fixed-16 is not, or if the curve is flat from low counts.
- H2: target-14-rotate preserves most of fixed-16 search performance
  with materially better late-operation readiness than fixed-14-hold
  or fixed-16. Falsified if it matches neither benefit.
- H3: rotation dominates hold at the same target after battery binds.
  Falsified if target-8/14-rotate and fixed-hold are indistinguishable
  on both find probability and residual capability.
- H4: escalation captures much of all-out early urgency only when the
  survivor is hard to find, while retaining capability when the find
  is easy. Falsified if it is dominated on both axes by a fixed policy.
- H5: far posture trades faster coverage for disproportionate
  attrition and lower second-request readiness. Falsified if it
  improves find probability without a readiness cost at these hazards.

## Sensitivity obligations

Conclusions may be drawn only after varying, at minimum: coordination
overlap (0, 0.055, 0.11), detection probability (0.70, 0.85, 0.95),
and hazard multiplier (0.5x, 1x, 2x). Any policy ranking that reverses
under these sweeps must be reported as parameter-dependent, not as a
strategy conclusion.

## Long-horizon extension (separate pre-registration required)

The same state variables scale to multi-request operations: repair
queues, replacement nodes, retained inter-node trust/reputation, and
fleet growth. In biological language, survival and reproduction are
fleet-health and capability-growth constraints; here they remain
engineering variables (serviceable fleet, energy, learned state), not
claims about biology. Explorer risk thresholds should be learned or
scheduled against explicit operational objectives, not copied from a
single-mission optimum.
