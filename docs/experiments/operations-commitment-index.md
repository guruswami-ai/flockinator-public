# Fleet-commitment experiments: index and synthesis

Supervisor-written synthesis of the commitment/reserve series.
Contributor draft reviewed and corrected (its seed ranges and
team sizes were invented); all numbers below are from the linked
evidence files. **Simulation only throughout**: commitment means
simulated sorties in a seeded virtual world, executed by host
code - not panel decisions, not aircraft.

| Study | Regime | Seeds | Headline |
|---|---|---|---|
| [Reserve screen](operations-reserve-dev-results.md) | Benign: 4 incidents, recharge +12 | 0-19 | Parking 2 of 16 costs nothing measurable; knee at K4-K8 |
| [Binding regime](operations-binding-results.md) | 8 incidents, recharge +4, damage grounds for window | 20-39 | Launching all 16 finds *fewer* over the day than park-2 (0.938 vs 0.981) |
| [Loss-bearing](operations-loss-bearing-results.md) | + p_fail 0.01, far 0.35, battery 75 | 40-59 | Committed 8 operationally best; all-16 loses most aircraft (0.90/window) |
| [Explorer fraction](explorer-fraction-results.md) | Loss-bearing, explorer minority | 60-79 | 1 explorer in K8: +2.5pt, faster; explorers harmful at K14 |
| [Explorer confirmatory](explorer-confirmatory-results.md) | Same, fresh seeds | 100-119 | Dev benefit **did not replicate** (0.644 vs 0.800) - falsified |

## Synthesis

The right commitment level is **regime-dependent**: the same
parked-2 policy that is free in a benign world beats all-16 in a
binding world and loses to a committed 8 in a loss-bearing one.
Slow escalation consistently trades away the scarcest resource
(daylight / time-to-find). Roster rotation never mattered.
The explorer result is the cautionary tale: a plausible,
theory-backed dev-split effect vanished on fresh confirmatory
seeds, which is why this programme pre-registers and confirms
before proposing anything.

Practical proposal (planner owner's decision, not ours): make
the parked count a **tested scenario parameter** rather than a
fixed constant, and judge strategies on operational metrics
(finds over the whole window, readiness for the next incident,
losses) rather than single-mission speed.

## Honest limits

All parameters (detect probability, failure rates, recharge,
damage rules) are assumptions with sensitivity sweeps reported
per study, not measured values from hardware. Strategies are
host-simulated policies; no panel has yet executed a scored
decision. The bridge to real node decisions is the
[panel-policy canary](panel-policy-canary-preregistration.md),
with the [host twin](../research/contributor-notes/sim-twin-prototype-spec.md)
implemented in `kulira_core/twin.py` as its parity comparator.
