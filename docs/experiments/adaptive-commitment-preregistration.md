# Pre-registration: adaptive commitment by distance (seeds 200-219)

Status: **pre-registered before this run.** Simulation only.
Commitment series conclusion so far: the best fixed commitment
is regime-dependent (operations-commitment-index). This tests
whether a scenario-dependent commitment - the proposal made to
the planner owner - beats both fixed neighbours.

Design: loss-bearing regime frozen (8 incidents, 160 turns,
recharge +4, ground-rest, p_fail 0.01, far 0.35, battery 75).
Arms: K8, K14, ADAPT (launch 8; if the incident's survivor is
far-class, top up to 14 at dispatch).

- **HA1:** ADAPT find rate >= K14 - 2pt (matches the big fleet
  where it matters). Falsified if ADAPT < K14 - 2pt.
- **HA2:** ADAPT lost <= K8 + 1 and ready-at-end >= K14 + 0.5
  (keeps the small fleet's operational profile). Falsified on
  either breach.
- Seeds 200-219, paired. A pass strengthens the scenario-
  dependent parked-count proposal; it changes no default.
