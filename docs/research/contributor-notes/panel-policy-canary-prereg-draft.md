<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Reviewed by supervisor before use; not yet adopted. Adapt host/framing details to Korvo + flockwire before implementation. -->

# Pre-registration Skeleton: ESP32-in-the-Loop Search Decision Test
**Study:** Simulated park search for lost hiker | **v0.1 - Pre-register before data collection** | All data simulated.

## 1. Setup
* **World host (controller):** Laptop/Python hosts shared virtual park grid, hiker position, signal field. Broadcasts `tick, robot_pose, signal, obstacle` via UDP/WiFi at 5 Hz.
* **Device under test:** 1x ESP32 panel computer (Arduino). Runs decision rule **locally**:
  ```
  if conf > 0.70: SEARCH (move toward signal)
  elif conf > 0.40: DOUBLE-CHECK (hold + resample)
  else: WAIT
  timeout >500ms with no packet: WAIT
  ```
* **Twin:** Host-computer Python function with identical rule, run on same inputs/seeds.
* **Scored evidence:** Only CSV logs on ESP32 SD-card. No host logs count for score.

`tick,seed,rx_hash,signal,conf,decision,latency_ms,free_heap,dropped_flag`

## 2. Hypotheses + Falsification
* **H1 Parity-perfect:** Under 0% loss, ESP32 decisions = twin on ≥99% ticks.
  *Falsified if parity <99% on any pre-reg seed.*
* **H2 Graceful degradation:** At 10% / 20% injected packet loss, parity ≥90% / ≥75%, no crash/reboot, and 100% of timeouts -> WAIT.
  *Falsified if below thresholds or any hang requiring manual reset.*
* **H3 Log completeness:** 100% ticks result in one SD-card row with valid timestamp, seed, rx_hash, decision.
  *Falsified if >0% missing/corrupt rows.*

## 3. Staged Gates - must pass to advance
* **Gate 0 Build:** Compiles, logs to SD, twin runs. N=10 ticks, seed 1.
* **Gate 1 Parity:** 0% loss, 10 seeds x 500 ticks. Pass = H1 holds.
* **Gate 2 Loss:** 5/10/20% loss, same seeds. Pass = H2 holds. Degradation must be monotonic.
* **Gate 3 Completeness audit:** Independent script diffs SD logs vs. twin. Pass = H3 holds + dropped packets accounted for.

Stop on fail, fix, re-register new version.

## 4. Metrics
* **parity_rate** = matched / total ticks per seed
* **decision_latency** = ms packet-received -> decision-sent; report median/p95
* **free_memory** = min `ESP.getFreeHeap()` per run; fail if <20kB
* **dropped_packets** = count + rate; from sequence gaps

Success: Gate1 parity ≥99%, p95 latency <200ms, zero SD gaps.

## 5. Seeds & Protocol
* **Fixed seeds:** `42, 101, 102, 103, 104, 105, 106, 107, 108, 109` - 500 ticks each. No re-seeding after start.
* **Procedure:** 1) flash frozen firmware, record hash 2) run Gate1->2->3 in order 3) remove SD, hash CSV, run `compare_twin.py` 4) report per-seed table.
* **Exclusions:** Runs with power loss or changed code excluded and reported.

## 6. Explicit Non-claims
Not testing real SAR effectiveness, real radio/GPS, 16-node scaling, optimal search, battery/outdoor robustness, or human-factors. Result is only: *can 1 low-cost node replicate twin logic live + log it.*

## 7. Timeline - 2-3 weeks
**Week 1:** Controller + twin + rule. **Week 2:** ESP32 firmware + SD logging + Gate1. **Week 3:** Loss injection + audit + report.
