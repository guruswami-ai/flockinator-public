## On-Device Render Perf Test - 8fps vs 15fps vs 30fps

**Goal:** Decide today if sim rendering can move from 8fps gate to 15fps or 30fps on 64x64 LED + ESP32-S3, worst-case included.

### 1. Builds to test (flash all 16 panels identically per run)

* **A - Baseline:** prod firmware, gate = 8fps (125ms budget)
* **B - Candidate 15:** same + gate = 15fps (66.6ms budget)
* **C - Trial 30:** trial build, gate = 30fps (33.3ms budget)

No code changes. Only gate flag differs.

### 2. Scenes - fixed seeds, fixed world

Use controller to broadcast `scene + seed`. All 16 panels render same scene in parallel.

1. `S1 Idle:` status grid, no raycast
2. `S2 Map:` top-down 64x64 map, 8 robots + trail
3. `S3 Raycast-Worst:` per-pixel raycast, face wall at 1m (max fill, no culling benefit)
4. `S4 Raycast-Open:` per-pixel raycast, open field + 8 robots + hiker + particles
5. `S5 Raycast+Alert:` S4 + alert banner + scrolling text overlay

Seeds: `101, 102`. Pre-register S3/seed-101 as primary decision scene.

### 3. Procedure per cell (Build x Scene)

Total: 3 builds x 5 scenes = 15 cells, all 16 panels in parallel.

1. Flash build, reboot, `diag reset`
2. Controller sends `set_scene Sx seed 101`, brightness 100%, white-balance fixed
3. Warmup 10s (discard, lets caches/LED DMA settle)
4. Run 60s steady, no touch / no OTA
5. `diag dump` -> log: `device_id, build, scene, seed, p50,p95,max, dropped, expected_frames, temp, uptime`
6. Next scene. Reboot between builds.

Time: ~80s/cell with overhead = ~25 min/run.

**Repeats:** Run 1x full matrix (n=16 per cell). Then repeat Sx=S3/S4 on builds B/C 1x more (n=32 for critical cells). Enough for today.

### 4. How to read out (existing diagnostics only)

Firmware already keeps last 256 frames. After step 5, capture:

```
p50_ms, p95_ms, max_ms, dropped_count
expected = gate_fps * 60
drop_% = dropped / expected
```

Note: 256 frames = 32s at 8fps, 8.5s at 30fps. 60s run = 2-7 full windows, valid.

Log to one CSV on controller + photos of 2x panels to catch tearing not in timers. No new tooling.

### 5. Pass / Fail thresholds

Evaluate per-scene pooled across 16 devices. Must pass **all 5 scenes** to adopt.

**Adopt 15fps if:**
* pooled p95 <= 55ms AND no device p95 > 60ms
* pooled max <= 66.6ms, drop_% < 1%
* zero reboots / watchdog / persistent tearing

**Adopt 30fps if:**
* pooled p95 <= 28ms AND no device p95 > 30ms
* pooled max <= 33.3ms, drop_% < 2%
* LED refresh stable, temp < 70C

**Decision:**
* Pass B, fail C -> ship 15fps sim, keep UI at 15fps.
* Pass both -> ship 30fps for raycast, optional 15fps cap for S5 if max marginal.
* Fail B -> stay at 8fps. Trial rejected.

One outlier device failing = FAIL. Investigate power/thermal on that unit, don't average it away.

### 6. Radio / SD contention risks - explicit sub-test

Biggest on-device lie: render looks fine with radio/SD idle, dies in sim.

After main matrix, on Build C + S3 only, 4 conditions, 60s each:
* R0/SD-off: WiFi idle, no SD log (baseline)
* R1/SD-off: controller streaming positions @10Hz
* R0/SD-on: SD logging on, radio idle
* R1/SD-on: both on (real sim condition)

Pass requires R1/SD-on still meets thresholds above. If p95 jumps >15% vs baseline, radio/SD is contending (SPI/DMA/core 0). Mitigation today: pin render to Core 1, SD flush to 512B/1s, drop telemetry to 5Hz, re-test.

Other guards: power all panels from mains (not USB hub), full-white S3 draws most current - brownout = invalid run. Leave 5cm air gap, log temp from diag.