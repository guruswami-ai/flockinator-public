## Live-sim upgrades: 6 ready-to-run experiments
Setup: controller holds true `32x32` grid + hiker pos, `TICK=200ms`. Panels run local rule: sense 3x3, move N/E/S/W, broadcast. Pre-register: 30 runs/condition, seeds `1000-1029`, log `time-to-find, coverage, messages`.

**1. Explorer fraction [REQUIRED]** Q: Does a small explorer minority speed find? Manip: `EXPLORERS = 0 vs 2 vs 4/16`; explorers use Levy step `sigma=3.0`, others `sigma=0.8`. Metric: ticks-to-find + % map covered at find. Needs live: coverage/redundancy tradeoff only emerges from local moves + collisions, can't be scripted.

**2. Trust / liar robot [REQUIRED]** Q: Can 1 liar derail consensus? Manip: `LIAR=none vs panel#7` broadcasts `hiker_here (conf=0.9)` from random false cell every 5 ticks. Metric: false-converge events, extra ticks-to-find, follow-rate. Needs live: requires real belief-update cascade across panels.

**3. Comms radius** Q: Local vs global sharing? Manip: share with `0 vs 2-nearest vs all-16` via allowlist filter in ESP-NOW. Metric: time-to-find, cluster size. Needs live: fragmentation vs consensus is an emergent network effect.

**4. Avoid-visited stigmergy** Q: Does repulsion help? Manip: `AVOID=false vs true` - penalize cells visited in last 20 ticks `-0.5` utility. Metric: overlap visits, ticks-to-find. Needs live: self-organized partitioning needs feedback. Code: <15 lines change.

**5. Dropout robustness** Q: How fragile is the swarm? Manip: controller sends `SLEEP` to `0 vs 4 vs 8` random panels at tick 100. Metric: % runs still find <500 ticks, delay slope. Needs live: re-coverage must self-organize.

**6. Moving hiker** Q: Can swarm track? Manip: `HIKER=static vs walk 1 cell/10 ticks` broadcast by controller. Metric: capture time, mean robot-hiker distance. Needs live: pursuit requires closed perception-action loop.

### Ranking table

| # | Experiment | Implementability this week (1=easiest) | Science value for emergence (1=highest) |
|---|---|---|---|
| 1 | Explorer fraction | **1** - config only | **3** - division of labor |
| 4 | Avoid-visited | **2** - local rule only | **4** - self-organization |
| 2 | Trust / liar | **3** - add false-msg gen | **2** - info cascade fragility |
| 5 | Dropout | **4** - sleep cmd | **5** - robustness |
| 6 | Moving hiker | **5** - controller move | **6** - tracking dynamics |
| 3 | Comms radius | **6** - neighbor filtering | **1** - local-to-global phase change |

Do **1, 4, 2** this week: no protocol change, highest signal per hour.
