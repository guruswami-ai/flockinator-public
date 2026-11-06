# Pre-registration: explorer fraction (seeds 60-79)

Status: **pre-registered before this variant was run.** Simulation
only. Contributor draft in `docs/research/contributor-notes/`;
freeze below is the supervisor's adaptation to this simulator.

Question: does allowing a minority of aircraft to range beyond the
systematic sweep (faster coverage, higher energy/risk exposure)
improve operational outcomes over a multi-incident day, and at
what cost? This is the cave-explorer hypothesis from the project
framing: most of the fleet stays systematic, a few take risks.

## Frozen setup

Loss-bearing regime (operations-loss-bearing): 8 incidents, 160
daylight turns, recharge +4, damage grounds for the window,
`p_fail 0.01`, far fraction 0.35, start battery 75.

Strategies K8 and K14, each with explorer fraction of the launched
force `f in {0, 1/16, 2/16, 4/16}` (explorer count = round(f*16),
capped at launched count). Explorers: coverage weight 1.6x per
turn, energy drain 2.0/turn (vs 1.1), return cost +4 (farther
from base). Selection and all other rules frozen.

## Hypotheses and falsification (paired by seed)

- **HE1:** f=2/16 improves find rate vs f=0 by >=3 points for at
  least one of K8/K14. Falsified if neither improves by 3 points.
- **HE2:** explorers cost readiness: mean ready-at-end falls
  monotonically-ish with f (f=4/16 ready <= f=0 ready - 0.5).
  Falsified if f=4/16 matches f=0 readiness within 0.5.
- **HE3:** time-to-find improves with f even where find rate does
  not (explorers help most on far survivors). Falsified if
  turns-to-find at f=2/16 >= f=0 for both strategies.

Seeds 60-79. Design-exposed; no holdout claim. Planner changes
remain proposals to the planner owner only.
