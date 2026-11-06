<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Supervisor-reviewed before use; not yet adopted. -->

### 3. Fleet-Commitment Experiments — Index

All results below are **seeded virtual-world simulations only** of robots searching for a lost hiker, run on 1 controller + 16 ESP32 panel computers acting as simulated agents. No field deployments. Each study was pre-registered with hypothesis, fixed seeds, sortie budget, and falsification condition before execution. See linked configs for full parameters and sensitivity sweeps.

| Exp | Regime | Commitment tested | Pre-registered falsifier | Simulated outcome |
|---|---|---|---|---|
| E1 Benign | Extra capacity redundant | 16 vs. 14 committed, 24h sim, seeds 1001-1100 | Fail if 14-team find-rate >2pp below 16-team | Park 2 of 16 costs nothing; find-rate and time-to-find identical |
| E2 Binding | Congestion / interference | 16 vs. 12 vs. 8 committed, 24h sim, seeds 2001-2100 | Fail if 16-team finds >= 12-team | Launching all 16 finds fewer over a day; 12-team best |
| E3 Loss-bearing | Attrition / robot loss | 8 vs. 12 vs. 16 committed, hazardous map, seeds 3001-3100 | Fail if 8-team not best on net finds minus losses | Committed 8 operationally best; all-16 loses most robots for no extra finds |
| E4 Explorer minority | Exploration mix | 0 vs. 1 vs. 3 explorers in teams of 8 and 14, seeds 4001-4100 | Fail if 1-explorer/8-team not faster on all speed metrics | 1 explorer in team of 8 slightly helps and speeds everything; explorers in team of 14 harmful |

**E1 - Benign: park 2.** With open terrain and low interference, 14 committed sorties matched 16 committed on probability-of-find and mean time-to-find. Parking 2 panels as reserve did not reduce day-1 finds. Retained as low-risk reserve policy.

**E2 - Binding: don't launch all.** With narrow corridors and overlapping sensors, full 16-team commitment caused blocking and re-search. Over a simulated day, 16 found fewer hikers than 12, and 12 beat 8. Supports binding constraint: commitment beyond ~12 is counterproductive.

**E3 - Loss-bearing: commit 8.** With hazard zones and per-sortie loss risk, expected net value peaked at committed 8. Teams of 12 and 16 added finds but lost disproportionately more robots; all-16 had highest gross sorties but highest losses and lowest net score. Committed 8 was operationally best.

**E4 - Explorer minority.** In a team of 8, adding 1 dedicated explorer slightly increased find-rate and improved all speed metrics vs. 0 explorers. Adding 3 explorers erased the gain. In a team of 14, any explorers reduced finds and slowed coverage due to dispersal and weak exploitation.

**Honest limits.** All simulated: commitment means simulated sorties launched in the virtual world, not real panel decisions, battery, comms, or weather yet. Map difficulty, sensor range, interference, and loss rates are assumptions, not measured values. Sensitivity to those parameters is reported per experiment, and conclusions will change if real-world calibration differs.
