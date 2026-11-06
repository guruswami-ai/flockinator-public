# Pre-registration: panel-policy canary (one node decides locally)

Status: **pre-registered, not yet run.** Adapted by the supervisor from a contributor-model draft (`docs/research/contributor-notes/`) to the real fleet: Korvo-hosted world, authenticated management channel separate from the simulation broadcast channel, tick-as-clock, one canary panel while the other fifteen keep current firmware. Firmware work is Drishdi-owned; this pre-registration is the Kulira-side experiment contract. Simulation world, real node execution, no aircraft.

---

**v1.0 near-final — register before data collection | All data simulated**

**Fleet:** 1x ESP32 controller (world host) + 16x ESP32 panels. **DUT:** 1 panel only (e.g. `PANEL-00` bench unit). Other 15 keep current display firmware, stay powered, ignore sim broadcast.

## 1. Setup (frozen for test)

**World host:** ESP32 controller unit, frozen `world_host.ino` + recorded `sha256`. Hosts virtual park grid, hiker position, signal field. No laptop in loop.

**Two channels, separated:**
* **SIM broadcast (scored input):** Unreliable broadcast @ 5Hz. Payload per tick: `tick, seed, robot_pose, signal, conf, obstacle, rx_hash`. No ACK, no retry.
* **MGMT unicast (control only):** Authenticated per-device frames, fixed **160B payload**. Pre-shared key + nonce. Commands only: `ASSIGN_SEED / START / STOP / REPORT_HASH`. No sim data here. Not scored.

**DUT rule (runs locally on panel):**
```
if no SIM packet for >500ms: WAIT (dropped_flag=1)
elif conf > 0.70: SEARCH
elif conf > 0.40: DOUBLE-CHECK
else: WAIT
```

**Twin:** Offline Python `twin.py` with identical rule. Runs on analysis machine after run, replaying SD inputs. Not on controller.

**Clock:** No fleet clock sync. **Simulation `tick` is the clock.** Ordering disputes resolved by `tick`. Panel `millis()/micros()` used only for `latency_ms` diagnostic.

**Scored evidence:** Only existing SD journal on DUT. Reuse `/sd/journal/search_test.csv`, append-only, flush per tick. No host logs count.
```
tick,seed,rx_hash,signal,conf,decision,latency_ms,free_heap,dropped_flag
# decision: 0=WAIT,1=DOUBLE-CHECK,2=SEARCH
```

## 2. Hypotheses + Falsification

* **H1 Parity-perfect:** At 0% loss, ESP32 decisions = twin on >=99% ticks per seed, seeds 80-99.
  *Falsified if any seed <99%.*
* **H2 Graceful degradation:** At 10% / 20% deterministic drop, parity >=90% / >=75%, zero crash/reboot, 100% of >500ms timeouts -> `WAIT`.
  *Falsified if below threshold, any hang needing manual reset, or any timeout != WAIT.*
* **H3 Log completeness:** 100% ticks yield exactly one SD row with valid `tick,seed,rx_hash,decision`.
  *Falsified if any missing/corrupt/duplicate tick.*

## 3. Staged Gates — stop on fail, fix, re-register

| Gate | Condition | N | Pass |
|---|---|---|---|
| **0 Build** | seed 40, 50 ticks, 0% loss | smoke | compiles, SIM+MGMT up, SD rows written, `twin.py` runs, other 15 displays unaffected |
| **1 Parity** | seeds 80-99, 500 ticks each, 0% loss | 10,000 ticks | H1 holds, p95 latency <200ms, min heap >20kB |
| **2 Loss** | same 20 seeds x 500 ticks at 5% / 10% / 20% drop | 30,000 ticks | H2 holds + monotonic: parity_0% >= parity_10% >= parity_20% |
| **3 Audit** | offline `compare_twin.py` SD vs twin | all | H3 holds + all drops accounted via seq gaps |

Loss injection: controller skips broadcast if `hash(seed,tick)%100 < loss%`. DUT unaware.

## 4. Metrics

* **parity_rate** = matched / total per seed. Report per-seed table + mean/min.
* **decision_latency** = ms RX-interrupt -> decision + journal flush. Median/p95 per seed. Fail if p95 >=200ms.
* **free_memory** = min `ESP.getFreeHeap()` per run. Fail if <20kB.
* **dropped_packets** = count + rate from `tick` gaps + `dropped_flag`. Must match injected rate ±1%.

Success: Gate1 >=99%, Gate2 thresholds met, zero SD gaps, zero reboots.

## 5. Seeds & Protocol (do today)

* **Fixed seeds:** 80-99 inclusive (20 seeds x 500 ticks). No re-seeding after START. Drop masks precomputed from seed.
* **Procedure:**
  1. Flash frozen `world_host.ino` + DUT firmware. Record both `sha256`, commit this file.
  2. Via MGMT 160B: `ASSIGN_SEED`, verify auth + `REPORT_HASH`. Start SIM broadcast.
  3. Run Gate 0->1->2->3 in order. No code change between gates or run is void.
  4. Remove SD, `sha256` CSV, run `compare_twin.py --seeds 80-99`. Publish per-seed table.
* **Exclusions:** Any run with power loss, code change, or MGMT failure excluded and reported. Do not silently replace.

## 6. Explicit Non-claims

Not testing real SAR effectiveness, real radio/GPS, 16-node scaling, optimal search policy, battery/outdoor robustness, human factors, MGMT crypto strength, or fleet clock sync. Claim is only: *can 1 low-cost panel replicate twin logic live + journal it while 15 peers run normally.*

## 7. Timeline / Artifacts

**Week 1:** Controller + `twin.py` frozen. **Week 2:** DUT firmware + journal + Gate1. **Week 3:** Loss + audit + report. Implementable today with: `world_host.ino`, `panel_dut.ino`, `twin.py`, `compare_twin.py`, 1 SD reader.
