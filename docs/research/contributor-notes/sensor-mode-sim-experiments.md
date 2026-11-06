<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Supervisor-reviewed before use; not yet adopted. -->

## Live shared-world sensor-mode experiments
**Setup:** 16x ESP32 panels = robots, 1x controller = world server. Shared seeded map, lost-hiker target. Simulated data only. Panels render one mode per search: Day, Thermal White-Hot / Black-Hot, Night, IR.

### E1: Diversity vs Uniformity
**Question:** Does fixed mode-diversity find the hiker faster than uniformity?
**Manipulation:** Between-search, same 20 target seeds `1001-1020`:
* Uniform: all 16x Day
* Diverse: 4x Day, 4x White-Hot, 4x Black-Hot, 4x Night/IR
No switching within search. Max 300 ticks.
**Primary metric:** Mean time-to-find; success rate if timeout.
**Falsification:** Falsified if Diverse mean time-to-find >= Uniform, or success rate Diverse <= Uniform.
**Why live on-device:** Tests real panel readability + local false positives/negatives under decentral detection. Host sim would use an oracle detector and miss display/human-factor limits.

### E2: Switching Cost
**Question:** Does a switching penalty reduce thrash without harming find time?
**Manipulation:** Within-search free choice from all modes:
* Free: instant switch
* Costly: 10-tick blackout + lockout on switch. Same seeds `2001-2020`.
**Primary metric:** Switches/search + time-to-find.
**Falsification:** Falsified if Costly does *not* reduce switches vs Free, or if Costly time-to-find is >20% worse than Free.
**Why live on-device:** Cost is display re-render, attention loss, and local state reset on ESP32. Host sim assumes zero-cost perfect switching.

### E3: Trust After Degradation
**Question:** Do robots abandon a degraded mode and maintain performance?
**Manipulation:** Two-phase, 20 seeds `3001-3020`:
* Phase A 0-150 ticks: all modes 95% detection
* Phase B: controller broadcasts White-Hot degraded to 30% detection, 40% false alarms. Each robot gets 1 voluntary switch.
Control: no degradation.
**Primary metric:** % leaving White-Hot in Phase B + post-degradation find rate.
**Falsification:** Falsified if <50% leave degraded mode, or degraded-group find rate = control.
**Why live on-device:** Requires autonomous on-panel trust update from local observations + one broadcast, no controller reassignment. Cannot be host-scripted without begging the question.

## Rank by implementability
**1 > 2 > 3**
1.  **E1 easiest:** static assignment at search start, no UI/state logic, minimal RAM/network.
2.  **E2 medium:** needs local switch button + timer/blackout, but no controller logic change.
3.  **E3 hardest:** needs live degradation broadcast, per-device detection jitter, logging of stay/leave decisions.
