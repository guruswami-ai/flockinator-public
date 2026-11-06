# Pre-registration: stall-triggered explorers (seeds 180-199)

Status: **pre-registered, not yet run in the fleet simulator.**
Simulation only. Follows the falsified always-on explorer result
(explorer-fraction seeds 60-79 and confirmatory 100-119): ranging
beyond the pattern from the start did not replicate. This variant
tests the mechanism the confirmatory results suggested - release
explorers only when the systematic search stalls. Contributor
draft in `docs/research/contributor-notes/`; implementation in
`kulira_core/operations.py` is required before any run (explorer
release is currently static per incident), so this document
registers the design ahead of that code.

## Design

Loss-bearing regime frozen (8 incidents, daylight 160, recharge
+4, ground-rest damage, p_fail 0.01, far 0.35, start battery 75).
Strategy K8. Arms by stall threshold T (turns without detection
progress before 2 explorers are released): T = never (control,
= f=0), T = 30, T = 60. Explorers use the registered explorer
mechanics (1.6x coverage, 2.0 drain, +4 return cost).

## Hypotheses

- **HS1 (primary, turns-to-find):** T=30 or T=60 is >=1.0 turn
  faster than control, paired by seed. Falsified if neither is.
- **HS2 (guardrail):** the best stall arm's find rate is no more
  than 3pt below control, and lost no greater. Falsified on
  either breach.
- **HS3:** T=60 loses fewer aircraft than T=30 (later release =
  less exposure). Falsified if T=60 lost > T=30 lost.

Seeds 180-199. If HS1 fails, the explorer line closes: two
independent falsifications (always-on, stall-triggered) are
enough. Planner relevance remains proposal-only.
