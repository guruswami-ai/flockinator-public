<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Supervisor-reviewed before use; not yet adopted. -->

## Critique: 8 vs 15 vs 30fps Render Gate Test

Pre-reg missing: state `H1: B p95<=55ms on S3/101 under load` / `H2: C p95<=28ms`, and falsifier. As written you can re-interpret after data.

### 1. Statistics: 256 frames cannot trust p95
- **Tail n too small:** p95 from 256 = ~13 frames in tail. 95% binomial CI spans ~7th-20th worst frame. One stall swings verdict by 5-15ms. Unstable per-device.
- **You don't log 60s:** you log *last* 8.5s at 30fps, last 32s at 8fps. Claim "2-7 full windows, valid" is false. Single window, recency-biased, misses warm drift.
- **Time-fixed = frame-unequal:** 60s = 480 frames @8fps vs 1800 @30fps. Tighter gate tested with more power, looser confidence at 8fps.
- **Pooled undefined:** pooled raw frames vs mean-of-p95s? "Pooled p95 <=55 AND no device >60" double-counts. With n=16 parallel, you have device variance, not temporal repeats.
- **Seed plan broken:** Seeds 101,102 listed, procedure only runs 101. S3/101 primary decision on 1 seed = overfit to one wall/particle layout.

### 2. Thermal / power drift
- **10s warmup != soak:** ESP32-S3 + 64x64 @100% white soaks in 8-15 min. S1->S5 fixed order means S4/S5 always hotter. No randomization, no cool-down, no temp-gate.
- **End-temp only:** `temp` in `diag dump` hides mid-run spike + throttling / LED driver derate. No ambient T logged.
- **Power guard weak:** "mains, 5cm gap" without brownout log, Vcc, or `brownout_count`. S3 full-white is peak current; one sag = slow SPI/DMA that looks like render miss.

### 3. Radio contention: main matrix measures fantasy
- Main 15 cells run radio-idle, then you decide ship. Sub-test only on C+S3 after decision data already collected.
- `R1: streaming @10Hz` undefined: unicast x16? multicast? ACKs? RSSI/channel? 16x parallel ACK storm is the worst case, not tested.
- No start-sync: controller broadcast latency = panels start seconds apart, different thermal/contention phase.

### 4. SD-write interference
- Same error: main matrix SD-off, real sim SD-on. SD stalls are 50-200ms long-tail — invisible in p95 from 256, kills `max`/`drop_%`.
- Cards not controlled: vendor/class/wear/fragmentation differ across 16 units. Flush size/frequency changes logging science data — can't mitigate day-of without pre-reg.
- `diag dump` over serial/WiFi may itself stall render; not isolated.

### 5. Decision thresholds contradictory & fragile
- **`max <= budget` will always fail at scale:** with 4k-28k frames pooled, one outlier = FAIL. Use p99/p99.9 + drop_%, not max.
- **Inconsistent:** drop <1% @15fps but <2% @30fps — looser for harder gate. Temp <70C only for 30fps.
- **All-5-scenes rule too strict then violated:** S1 Idle should not block raycast gate. Then "Pass both -> cap S5 at 15fps if marginal" violates "must pass all 5."
- **Tearing subjective:** photos of 2/16 panels, no definition of persistent vs 1-frame tear.

---

### Required Edits List
1. **Log all frames, not 256:** stream `frame_id,dt_ms` via UART to controller CSV per device. Target >=1500 frames/device/cell. Run by frames not seconds: 1500 frames = 187s @8fps, 100s @15fps, 50s @30fps.
2. **Fix p95 method pre-reg:** pooled p95 from raw frames + per-device p95/p99 with binomial 95% CI. No mean-of-p95s. Require `n>=1000` to claim p95 ±2ms.
3. **Run under load:** main matrix with R1/SD-on (10Hz positions unicast, SD 512B/1s). Keep R0/SD-off as diagnostic only, not decision data.
4. **Randomize + temp-gate:** randomize scene order per device block, 3 min cool to <45C between cells, log temp+voltage @1Hz + `brownout/reboot_count`. Abort cell if drift >10C.
5. **Fix seeds:** run 101 *and* 102 for S3/S4 on B/C. Primary stays S3/101, must replicate on 102 within 10%.
6. **Define contention:** fix WiFi ch, multicast, RSSI>-60dBm, log `rx_loss%, retry`. Sync start with controller `t0` beacon.
7. **Standardize SD:** same card model, full format, pre-fill test. Report `max, p99.9, drop_%` — p95 alone hides SD stalls.
8. **Rewrite thresholds:** Adopt if under load: `p95<=budget-15% AND p99<=budget AND drop<1%` for *S3+S4+S5 only*, zero watchdog/reboot, no sustained tear >2s. Same drop for 15/30. Remove `max<=budget` and S1/S2 veto.
9. **Remove post-hoc cap:** no "cap S5 at 15fps" unless pre-registered. Pass both = ship 30fps, else 15fps.
10. **Reboot + `diag reset` between every cell,** log `uptime, free_heap` to catch leaks.