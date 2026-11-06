<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Supervisor-reviewed before use; not yet adopted. -->

## Pre-registration: Explorer Minority in Simulated Search Fleet

**Study:** Seeded virtual-world search, 16 searcher robots + 1 controller on ESP32 panels. Simulated data only. No human subjects.
**Date frozen:** 2026-11-06
**Design:** Within-seed comparison, 4 conditions x 20 days x 8 searches/day = 640 searches.

### 1. Conditions
Explorer fraction of 16-robot fleet, rest sweep systematically:
- **C0:** 0/16 (0 explorers, pure sweep)
- **C1:** 1/16
- **C2:** 2/16
- **C4:** 4/16

Explorers may leave group pattern with long-range jumps; sweepers follow lawnmower pattern.

### 2. Hypotheses + Falsification

**H1 - Find rate:** C1 and C2 > C0, with diminishing returns: C4 <= C2.
> *Falsified if:* mean per-day find rate for C1 and C2 is not > C0, or C4 > C2 by >5pp.

**H2 - Time-to-find:** Conditional time-to-find (turns, successes only) is lower with any explorers vs C0.
> *Falsified if:* mean turns-to-find in C1, C2, C4 is not < C0 by >=5 turns.

**H3 - Unavailability cost:** Robot unavailability over the day increases monotonically: C0 < C1 < C2 < C4.
> *Falsified if:* ordering violated, or C4 unavailability not > C0 by >=2pp.

All means: average of per-day means across seeds 60-79, paired by seed. Decision on 95% bootstrap CI of paired difference (10k resamples).

### 3. Frozen Parameters
- **World:** 64x64 grid, 10% obstacles, 1 lost hiker with random walk, detection radius 2 cells, max 200 turns/search.
- **Day:** 8 sequential searches/day, battery carries over, hiker placement sequence identical across conditions within seed.
- **Battery reserves:** Start 100. Cost: 1/search-turn sweeper, 2.5/explorer turn. If <25: return, unavailable next search. Recharge +30 between searches, max 100.
- **Faults:** p=0.01 / robot-turn independent. Fault = lost for remainder of that search + next search unavailable.
- **Seeds frozen:** 60-79 inclusive. One seed = one full 8-search day. No resampling, no code changes after start.

### 4. Metrics
- **Primary:** Find rate = successes / 8 per day. Time-to-find = turns to first detection, successes only, 200 if fail for secondary analysis.
- **Cost:** Unavailability = robot-searches unavailable at search start / (16*8) per day.
- **Report:** Means ± SD across 20 days, paired differences vs C0, CIs. No subgroup peeking.

### 5. Follow-up Rule
Run follow-up (adaptive 2/16 + battery-aware recall) **only if** H1 and H3 both hold. If H1 falsified, freeze explorer-fraction manipulation and report null; no testing of 3/16, 6/16 until new pre-registration.
