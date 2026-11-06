# Pre-registration: explorer confirmatory, K8 + 1 explorer (seeds 100-119)

Status: **pre-registered before this run.** Simulation only.
Follow-up to explorer-fraction (seeds 60-79), where K8 + 1/16
explorers gave +2.5pt finds and faster times but below the
registered 3pt threshold. Contributor follow-up draft in
`docs/research/contributor-notes/`.

Design: loss-bearing regime frozen (8 incidents, 160 turns,
recharge +4, ground-rest damage, p_fail 0.01, far 0.35, start
battery 75). Arms: K8 f=0 vs K8 f=1/16, paired by seed.

- **Primary metric:** mean turns-to-find (paired difference).
  HC1: f=1/16 is faster by >=1.0 turn on average. Falsified if
  the paired mean difference is < 1.0 turn.
- **Secondary:** find rate (guardrail: f=1/16 no more than 3pt
  below f=0), lost, ready at end.
- Seeds 100-119 (fresh to the programme). A pass justifies
  proposing K8 + 1 explorer as the starting configuration for a
  future live panel test; it does not change any planner default.
