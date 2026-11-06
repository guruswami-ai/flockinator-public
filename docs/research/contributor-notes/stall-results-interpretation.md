<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Supervisor-reviewed before use; not yet adopted. -->

## Stall-triggered explorers: simulated result

Pre-registered test on seeded virtual-world search (16x ESP32 panels + 1 controller, robots searching for a lost hiker). **Simulated data only.**

| Condition | Find rate | Mean turns | Losses |
|---|---|---|---|
| Control | 86.9% | 9.2 | 1 |
| Release explorer at turn 30 if stalled | 82.5% | 11.0 | 2 |
| Release explorer at turn 60 if stalled | 86.9% | 9.2 | 1 |

Earlier confirmatory run of **always-on** explorers also failed.

### Honest interpretation
- **Turn-30 trigger hurt:** -4.4 pp find rate, +1.8 turns, +1 loss vs control. Direction is consistently worse, not neutral.
- **Turn-60 trigger did nothing:** identical to control on all three metrics. This is not a success; it means the intervention had no measurable effect in this simulation, likely fired too late or too rarely to matter.
- **Convergent null:** Two explorer concepts (always-on and stall-triggered) have now failed. This is not bad luck on one seed.

### What to conclude
The explorer hypothesis is falsified for this setup: adding explorers, either always or on stall, does not improve find rate, speed, or safety.

### What to stop doing
- Stop tuning explorer release turns, counts, or stall thresholds under current world assumptions.
- Stop post-hoc re-analysis to find a subgroup where explorers "almost work."
- Stop spending panel/controller time on confirmatory explorer runs without a new pre-registered rationale.

### What remains open
- Only new mechanisms: e.g., better base search policy, communication, or loss-avoidance — tested as fresh pre-registrations with fixed seeds, not explorer variants.
- Publish/archive this as a clean negative result.