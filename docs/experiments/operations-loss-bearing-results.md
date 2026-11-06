# Results: loss-bearing commitment regime (seeds 40-59)

Run under
[operations-loss-bearing-preregistration.md](operations-loss-bearing-preregistration.md).
Evidence: `validation/kulira/operations-loss-bearing-001.json`.
Simulation only. Regime: binding settings plus `p_fail 0.01`,
far fraction 0.35, start battery 75.

| Strategy | Find rate | Turns | Ready end | Ready inc2 | Ready inc5 | Damaged | Lost/window | Unattempted |
|---|---|---|---|---|---|---|---|---|
| K8 | 0.756 | 12.5 | 10.05 | 15.2 | 12.55 | 119 | 0.00 | 0 |
| K8R | 0.763 | 12.5 | 9.80 | 15.2 | 12.50 | 122 | 0.10 | 0 |
| K14 | 0.638 | 7.0 | 9.40 | 15.1 | 12.95 | 124 | 0.40 | 0 |
| K16 | 0.581 | 7.3 | 7.05 | 14.6 | 12.20 | 161 | 0.90 | 1 |
| ESC | 0.638 | 20.5 | 10.40 | 14.7 | 12.20 | 112 | 0.00 | 0 |

Miscalibration check first: pooled mean lost 0.28/window, inside
the registered 0.2-6 band - verdicts stand.

- **HL1 supported.** Losses scale with airborne exposure: K16
  0.90/window > K14 0.40 > K8R 0.10 > K8/ESC 0.00. The loss axis
  finally discriminates, and it discriminates *against* launching
  everything.
- **HL2 falsified.** K14 has no unattempted problem (0 vs K16's
  1), but its find-rate cost vs the best strategy is 12.5 points,
  over the registered 5-point limit. In a loss-bearing world the
  parked-2 fleet is safer than all-16 but finds materially fewer
  survivors than a committed 8.
- **HL3 falsified as stated.** ESC ties K8 at zero lost +
  unattempted; it is not uniquely safest, and it is by far the
  slowest to find (20.5 turns).
- **The operational winner here is K8** (joint-best finds, no
  losses, 10 ready at end), with K8R equal on finds but one loss
  event across the split. That inverts the benign-regime result,
  where K14 weakly dominated: **the right commitment level is
  regime-dependent**, which is precisely why the parked count
  should be a scenario parameter to test, not a constant to
  assume. This remains a proposal for the planner owner; no
  planner or firmware change is made here.
