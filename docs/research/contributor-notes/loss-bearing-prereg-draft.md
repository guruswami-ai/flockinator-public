<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Reviewed by supervisor before use; not yet adopted. Adapt host/framing details to Korvo + flockwire before implementation. -->

# Pre-registration: Fleet-Size Simulation v2-HARD
**Simulated study only - no real robots, hikers, or field data.**

## 1. Background
- v1 result: fleet N=16, 5 strategies [Send-8 static, Send-8 rotating, Send-14, Send-16, Escalating] all had **0 robots unavailable for rest of simulated day**.
- Metric `unavailable_robots` at ceiling, cannot discriminate strategies.
- v2-HARD goal: introduce plausible attrition so availability trades off against detection.

## 2. Frozen simulated setup
- Park: 20x20 grid, 1 lost hiker per search, random walk.
- Day: 5 sequential searches, Search 1..5. Sensors and speed identical across robots.
- Fleet: 16 identical search robots.
- Strategies (between-runs arm):
  - **S8:** same 8 every search
  - **R8:** 8 rotating (least-used ready first)
  - **S14:** 14
  - **S16:** all 16
  - **ESC:** 8 -> if fail, 10 -> 12 -> 14 -> 16, only ready robots
- Recharge: 1 search downtime after 1 search out, unless unavailable.
- Execution: 20 seeds **40-59** x 5 arms = 100 simulated days, run batched on 16 nodes, deterministic per seed.

## 3. Proposed difficulty mechanisms
Calibrated to produce ~5% daily attrition for S8 and ~20-40% for S16, avoiding floor/ceiling. Ranges from pilot sweeps on seeds 1-5 (excluded from confirmatory):

1. **Random mechanical faults:** `p_fault = 0.02 - 0.08 / sortie`, proposed freeze at **0.05**. Justification: MTBF field data ~20 sorties; creates strategy-independent baseline.
2. **Long-trip battery strain:** if simulated trip distance > 75th percentile, `p_battery = 0.10 - 0.30`, proposed freeze at **0.20** -> unavailable. Justification: larger teams range farther, penalizes over-send.
3. **Bad-weather attrition:** per-search `p_weather = 0.10 - 0.25`, if event then each deployed robot `p_loss = 0.10`, proposed freeze at **0.15 / 0.10**. Justification: correlated loss, punishes putting all robots at risk at once.

Final v2-HARD freeze: `p_fault=0.05, p_battery=0.20, p_weather=0.15, p_loss|weather=0.10`. No changes after seed 40 run starts.

## 4. Hypotheses + falsification

- **H1 Efficacy vs attrition:** S16 > S14 > S8 in `hikers_found`, but S16 > S14 > S8 in `unavailable_robots`.
  - *Falsified if:* ordering fails on either metric by two-sided permutation test p>=0.05, or S16 mean unavailable <1.0 robot/day.
- **H2 Rotation protects:** R8 >= S8 on `hikers_found`, R8 < S8 on `unavailable_robots`.
  - *Falsified if:* R8 unavailable >= S8, or R8 finds >0.5 fewer hikers/day than S8.
- **H3 Escalating balances:** ESC non-inferior to S16 on `hikers_found` (margin -0.5/day) AND ESC < S16 on `unavailable_robots` by >=1.5 robots/day.
  - *Falsified if:* either clause fails.
- **H4 Readiness collapse:** `readiness_before_5` S16 < R8 < ESC; no difference at `readiness_before_2`.
  - *Falsified if:* ANOVA across arms p>=0.05 at Search 5, or p<0.05 at Search 2.

## 5. Metrics (per seed/day)
- `hikers_found`: 0-5
- `unavailable_robots`: 0-16 at end of day
- `followups_never_attempted`: 0-4, count where <4 ready so follow-up cannot launch
- `readiness_before_2, _before_5`: n_ready /16

## 6. Follow-up rule
- **In-sim:** failed search triggers follow-up only if >=4 ready robots; else log as `never_attempted`, skip.
- **Experimental:** if H1-H4 all falsified due to too-low (<10%) or too-high (>60%) attrition, one recalibration allowed with new seeds 60-79, pre-registered as v2-HARDb. No seed re-use.
