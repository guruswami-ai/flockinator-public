# Pre-reg Critique: Fleet-Size v2-HARD — Not ready to freeze

**Simulated only. Verdict: fix deploy/recharge contradiction + re-derive attrition math before running seeds 40-59.**

## 1. Are difficulty mechanisms plausible + independent?

1.  **`p_fault` — OK, keep.** Strategy-independent per-sortie risk is correctly motivated. MTBF ~20 sorties = `p=0.05` is plausible, but math is wrong for your target (see §2).
2.  **`p_battery` on `>75th percentile distance` — NO, as written favours small teams by construction.** Problems:
    * Percentile of what? Within-search percentile guarantees 25% flag rate in *every* arm, no differential unless you prove S16 travels farther/robot.
    * In most sweep models more robots = *less* distance/robot. Your justification "larger teams range farther" inverts this. You need to log it.
    * Fix today: use **absolute threshold** from v1 logs, frozen from pilot seeds 1-5. E.g. `if trip_cells > 120 then p_battery`. Motivation: battery datasheet, not pilot-tuning to punish S16.
3.  **`p_weather` — plausible but explicitly anti-large.** Correlated loss only hits deployed robots, so S16 always pays 2x S8. That's realistic, but then you have *two* pro-small mechanisms and zero pro-large mechanisms. Stacked deck for ESC/R8.
    * Fix today: add independent counterweight and pre-register it: e.g. `p_miss_due_to_coverage` — small teams have lower per-search `p_find`. That's already in sim, but make it explicit so H1 is a real tradeoff, not attrition theatre. Cite external weather log for `p_weather`, don't tune it to hit 20-40%.

## 2. Parameter ranges don't hit stated targets

Your target: S8 ~5% daily = 0.8 robots/day, S16 20-40% = 3.2-6.4/day.

Expected faults alone:
* S8: 40 sorties * 0.05 = **2.0/day** — already 2.5x target before battery/weather.
* S16: 80 sorties * 0.05 = **4.0/day** — already at ceiling before other layers.

Proposed freeze overshoots into floor/ceiling (>60% attrition for S16 once you add battery + weather). Ranges `0.02-0.08`, `0.10-0.30`, `0.10-0.25` are wide enough to matter, but centered too high.

Freeze lower, justify from pilots 1-5 without peeking at 40-59.

## 3. Hypotheses not falsifiable as written

* **H1:** "Falsified if p>=0.05" conflates *failed to confirm* with *falsified*. Pre-specify paired (by seed) two-sided permutation test, directional prediction + manipulation check: `mean_unavailable_S16 <1.0 => miscalibrated, H1 void`.
* **H2:** No mechanism for R8 < S8 if faults are i.i.d. per sortie and total sorties equal (40 vs 40). Only works if battery strain is cumulative. State it or drop H2.
* **H3:** Non-inferiority margin -0.5/day on 0-5 scale + superiority >=1.5 robots/day with n=20 seeds needs power check. Pre-specify Holm correction across H1-H4, paired test, no post-hoc margin change.
* **H4:** Predicts *no difference* at Search 2, but under your recharge rule S16 sends 16 in Search 1 -> 0 ready before Search 2, S8 has ~8 ready. Difference is guaranteed. H4 false by construction.
* **HARDb rule:** "if H1-H4 all falsified due to <10% or >60% attrition, recalibrate on 60-79" = result-conditional researcher DF. Replace with blinded manipulation check independent of H-tests.

## 4. Blockers / confounds — fix today

1.  **Deploy vs recharge contradiction:** "1 down after 1 out" makes "S8 same 8 every search" and "S16 every search" physically impossible. Must define as `deploy = min(target, n_ready)`. Log `deployed_n`.
2.  **Day structure ambiguous:** 5 sequential searches = 5 new hikers, or 1 hiker + up to 4 follow-ups? `followups_never_attempted 0-4` implies latter. Freeze: Search 1 always launches; Search k+1 follow-up only if previous failed AND `n_ready>=4`.
3.  **Hiker path not frozen across arms:** Must use same world seed for all 5 arms within confirmatory seed. Separate RNG streams: `rng_world(seed)`, `rng_fault(seed,arm)`, `rng_weather(seed)`. Otherwise arm effect confounded with difficulty.
4.  **S8 definition:** which 8? Freeze IDs 0-7, prefer lowest-ID ready; R8: least-used ready, tie-break lowest-ID. ESC: targets [8,10,12,14,16] on attempt number, capped by `n_ready`, needs `>=4` to launch.
5.  **Percentile leakage:** don't compute battery threshold per-search-per-arm. Freeze global threshold from pilots.
6.  **Execution:** 16 nodes must be isolated, no shared state. Log code commit hash, store per-seed-per-arm CSV, forbid re-running 40-59.
7.  **Analysis peeking:** freeze analysis script before seed 40 starts.

## 5. Recommended frozen table to register

| Param | Freeze | Notes |
|---|---|---|
| Park / hiker | 20x20, 1 hiker/search, random walk frozen per seed across arms | `rng_world = seed` |
| Day | 5 attempts max; Attempt1 always; Attempt k+1 only if fail + `n_ready>=4` else `never_attempted+=1` | clarifies metric 0-4 |
| Fleet | 16 identical, speed/sensor equal | |
| Arms (target, deploy=`min(target,n_ready)`) | S8: fixed IDs 0-7 preference; R8: least-used ready; S14: up to 14; S16: up to 16; ESC: [8,10,12,14,16] by fail-count | tie-break lowest-ID |
| Recharge | 1-search downtime after sortie; `unavailable` never returns | |
| `p_fault` | **0.01 / sortie** | MTBF 100 sorties; baseline, arm-independent |
| `p_battery` | **0.10 if `trip_cells > T`, else 0; T=120 frozen from seeds 1-5 median** | absolute, from battery spec + v1 logs |
| `p_weather`, `p_loss` | **0.10, 0.05** per-search event, then per-deployed | from local weather log, not tuned |
| Expected | S8 ~0.5-1.5 unavail/day; S16 ~2.5-6.0/day | manipulation check, blinded |
| Seeds | pilots 1-5 (tuning only); confirmatory **40-59 x 5 arms =100 days**, paired by seed | no re-use; commit hash logged |
| Metrics/day | `hikers_found 0-5`, `unavailable_robots 0-16 EOD`, `never_attempted 0-4`, `readiness_before_2/5`, `deployed_n` | |
| Tests | paired permutation by seed, two-sided α=0.05 Holm H1-H4; H3 non-inf margin -0.5 + superiority 1.5 | freeze script pre-run |
| Miscalibration rule | if pooled S16 mean <1.0 or >9.6 (>60%) OR S8 mean >4.8, declare miscalibrated, do **not** test H; register HARDb with seeds 60-79 | independent of H direction |

Register this table + commit hash + analysis script, then run 40-59 once.
