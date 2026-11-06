<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Supervisor-reviewed before use; not yet adopted. -->

## Fleet Commitment: How Many to Launch? — Synthesis

**Simulated data only.** 16 small ESP32 panel computers + 1 controller ran a seeded virtual-world search: robots searching for a lost hiker. No field data. All experiments were pre-registered with hypotheses, falsification criteria, and fixed seeds.

Question: given 16 available, how many should you commit?

Answer: **it depends on regime.** Parked-reserve count should be a tested scenario parameter, not a fixed assumption.

### 1. Benign regime: 14 = 16, knee at 4-8

With ample searches and recharge, launching all 16 gave no meaningful gain over launching 14 and parking 2 as reserve.

Performance vs. team size was strongly sublinear: the knee was at **4-8 robots**. Going from 2 to 8 helped a lot; going from 8 to 14 helped a little; 14 to 16 was flat within noise.

Falsification passed: more was not proportionally better. Operational reading: in easy conditions, keep 2 parked for redundancy / late-day replacement at zero cost to finds.

### 2. Binding regime: launching all 16 found *fewer* than parking 2

With more searches required and less recharge available, energy became binding. Here **14 beat 16 over the full day.**

Launching 16 created early contention for charge and overlapping search, leaving the fleet depleted mid-day when new tasks arrived. Parking 2 smoothed consumption.

Two other tactics failed:

* **Rotation was useless:** cycling fresh robots in did not increase total finds. The bottleneck was total energy/day, not tired individuals.
* **Slow escalation wasted daylight:** starting small and ramping up missed morning opportunities and never caught up.

Pre-registered prediction confirmed: under constraint, maximal commitment is actively harmful.

### 3. Loss-bearing regime: committed 8 was best

With risk of robot loss per sortie, full commitment was fragile. Launching all 16 lost **~0.9 robots/day on average** — most of the fleet gone quickly across repeated days.

A committed team of **8 was operationally best**: enough parallel search to find the hiker quickly, small enough to limit exposure and preserve a viable fleet for tomorrow. Smaller than 8 found too slowly; larger than 8 burned robots for little time gain.

This is the clearest regime-dependence: best = 14 in benign, 14 in binding, 8 in loss-bearing. No single number works.

### 4. Explorers: help small teams, hurt large teams

Adding dedicated explorers (robots that scout rather than exploit known clues):

* In an **8-team, +1 explorer slightly helped** finds and **everything got faster** — time-to-first-clue and time-to-find both fell.
* In a **14-team, explorers were harmful.** The large team already covered space; explorers added movement and energy cost without new information, reducing total finds.

Exploration is not universally good; its value falls as coverage saturates.

### Takeaway

| Regime | Best commit (of 16) | Lesson |
|---|---|---|
| Benign | 14 = 16 | Park 2 for free |
| Binding (energy) | 14 > 16 | Full launch depletes fleet |
| Loss-bearing | 8 best, 16 loses 0.9/day | Commit less to survive |
| + Explorers | Helps 8, hurts 14 | Don't add scouts to saturated team |

Do not hard-code "launch all." Test `N_parked = 0, 2, 4, 8` as a scenario parameter in planning.

**Limits:** toy simulator, simplified battery / loss / detection models, no weather, terrain, comms failure, or human factors. Results show logic to test, not field doctrine.
