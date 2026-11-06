# Results: adaptive commitment by distance (seeds 200-219)

Run under
[adaptive-commitment-preregistration.md](adaptive-commitment-preregistration.md),
loss-bearing regime. Evidence:
`validation/kulira/adaptive-commitment-001.json`. Simulation only.

| Strategy | Find rate | Turns | Ready end | Lost | Damaged | Unattempted |
|---|---|---|---|---|---|---|
| K8 | 0.769 | 11.5 | 9.95 | 2 | 119 | 0 |
| ADAPT (8, far->14) | 0.694 | 10.0 | 9.90 | 5 | 117 | 0 |
| K14 | 0.656 | 7.7 | 9.15 | 8 | 129 | 1 |

- **HA1 falsified.** ADAPT (0.694) does not match K14 (0.656)
  within 2pt - it *beats* it by 3.8pt, so the "matches" framing
  fails in the favourable direction on finds, but…
- **HA2 falsified.** ADAPT loses 5 aircraft vs the registered
  ceiling of K8 + 1 (= 3). Readiness passes (9.90 >= 9.65), the
  loss guardrail does not.

Reading: topping up on far incidents buys finds over fixed-14
and keeps fixed-8 readiness, but the extra far exposure still
costs hulls. Adaptive commitment is better than either fixed
neighbour on the finds/readiness pair and worse than fixed-8
on losses. Whether that trade is worth it is an objective-
profile decision (life-first vs fleet-preserving), not a
dominance result - and exactly the kind of scenario-dependent
choice the planner proposal should expose rather than hide.
