# Results: explorer fraction (seeds 60-79)

Run under
[explorer-fraction-preregistration.md](explorer-fraction-preregistration.md)
in the loss-bearing regime. Evidence:
`validation/kulira/explorer-fraction-001.json`. Simulation only.

| Strategy | f | Find rate | Turns | Ready end | Damaged | Lost | Unattempted |
|---|---|---|---|---|---|---|---|
| K8 | 0 | 0.744 | 11.8 | 10.50 | 109 | 1 | 0 |
| K8 | 1/16 | 0.769 | 9.4 | 10.70 | 106 | 0 | 0 |
| K8 | 2/16 | 0.725 | 10.3 | 11.50 | 90 | 0 | 0 |
| K8 | 4/16 | 0.694 | 8.2 | 11.25 | 93 | 2 | 0 |
| K14 | 0 | 0.663 | 8.0 | 8.30 | 146 | 8 | 0 |
| K14 | 1/16 | 0.600 | 7.9 | 6.20 | 183 | 13 | 0 |
| K14 | 2/16 | 0.606 | 6.2 | 7.55 | 156 | 13 | 0 |
| K14 | 4/16 | 0.594 | 6.1 | 6.50 | 178 | 12 | 1 |

- **HE1 falsified.** No explorer fraction improves find rate by
  the registered 3 points. Best case is K8 with one explorer
  (+2.5 points); everywhere else explorers reduce finds.
- **HE2 falsified for K8, supported for K14.** At K8, readiness
  does not fall with explorer fraction (faster finds end sorties
  sooner, offsetting higher drain). At K14 readiness collapses
  (8.3 -> 6.2-7.6) and damage jumps - with 14 already airborne,
  explorers mostly add exposure.
- **HE3 supported.** Time-to-find improves with explorer
  fraction in both strategies (K8 11.8 -> 8.2 turns; K14 8.0 ->
  6.1). Explorers buy speed, not probability.

Reading: the cave-explorer effect exists but is narrow - one
explorer in a moderate commitment finds slightly more and
everything finds faster; beyond that, or in an already-large
commitment, ranging afield is pure risk. If a future live
experiment tests explorer behaviour, the registered starting
point should be K8 + 1 explorer, with time-to-find as the
primary metric rather than find rate. Proposal only; planner
decisions remain with the planner owner.
