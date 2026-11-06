<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Supervisor-reviewed before use; not yet adopted. -->

# Distributed flight sim — implementation breakdown

**Status:** design only, nothing built. All work is **simulated data only**, seeded virtual-world search (16 robots / lost hiker). Each experiment pre-registered with hypothesis + falsification + fixed seed.

**Starts from:** `recon::scene()` scripted theatre (`shared/recon/model.h`), `world::render()` 64x64 raycaster (`node-platform/include/world_render.h`), `mission_world.h` 16-pose loop, `flockwire` 160B payload (`shared/commissioning/wire.h`), ESP-NOW link (`node_link.cpp`), Korvo clock/journal authority.

## Work packages

| WP | Title | Deps | Days |
|---|---|---|---|
| 0 | Pre-reg, seeds, harness | — | 2 |
| 1 | Controller sim core @10Hz | 0 | 5 |
| 2 | Snapshot/intent wire codec + transport | 0 | 4 |
| 3 | Panel interpolation + local rendering | 1,2 | 5 |
| 4 | Panel local decision rule | 3 | 3 |
| 5 | SD journaling + readback scoring | 1,2 | 3 |
| 6 | Host simulation twin | 1,2 | 4 |
| 7 | 16+1 fleet integration test | 3,4,5,6 | 5 |
| 8 | GPU-offload fallback spike (optional) | 6 | 3 |

Total ~31d serial; ~18d with 2-3 devs parallel. **Critical path: 0 → 1 → 3 → 7.** WP2 also on critical path — must close before WP3 starts.

### WP0 — Pre-reg + seeds + harness (2d)
Define 3-5 seeded scenarios (target appear, link loss, modality betray). Fix seeds, tick count (e.g. 6000 ticks = 10 min @10Hz), falsification thresholds.
- **Accept:** `docs/experiments/*.md` merged; `tools/check_seed.py` reproduces world hash from seed alone; CI fails on unregistered seed.

### WP1 — Controller sim core @10Hz, Korvo (5d)
Kinematic quadcopter only: velocity-lag + drag + turn-limit + clamp. Fixed-point state: existing `recon::State:uint8` + sensor enum. No dynamics, no learning.
- **Accept:** 10Hz tick jitter <5ms over 10min; tick cost <0.5ms on Korvo; determinism: same `seed+run` ×600 ticks = identical SHA256 state hash on 3 runs.

### WP2 — Snapshot/intent wire format (4d)
Canonical: 24B/aircraft (pos/vel/att fixed-point) → 384B + 8B header = **392B snapshot**; intent 4B/node → ~72B/tick aggregate. Does **not** fit `flockwire` 160B or ESP-NOW v1 250B.
Decide: ESP-NOW v2 (1470B, 1 frame) vs Wi-Fi/UDP (~1200B, 1 frame) vs 3× fragmented `flockwire`. Add `tick, run_id, crc`.
- **Accept:** codec round-trip fuzz 1M vectors pass; on-air size measured: snapshot ≤400B, intents ≤80B; loss test 10% → decoder never crashes, flags `stale`; rate ≤6kbps broadcast + overhead.

### WP3 — Panel interpolation + local rendering (5d)
Replace `recon::scene()` source-of-truth with live snapshot. Dead-reckon 10Hz → 20-30fps display: lerp pos, slerp heading, hold-last on drop >500ms → mark `stale`. Reuse `world::render()` + `mission_world.h` peer list, 8KB RGB565 double buffer.
- **Accept:** with 0% loss pose error = 0 at tick boundary; with 10% loss <0.5m drift for 1s; render ≥20fps on ESP32-S3, no PSRAM alloc in frame loop; sensor palette (Cam/Night/WH/BH/IR) matches reference frames.

### WP4 — Panel local decision rule (3d)
Deterministic policy only, no inference. Inputs: interpolated poses + director events. Outputs: `CLAIM/SHARE/CHECK + sensor switch`. Kulira rule: `direct_verified` only may commit; close-call → abstain.
- **Accept:** replay of WP0 scenarios: precision/recall within ±2% of Python reference; zero commits on `indirect` provenance; 6000-tick run journaled bit-identical on 2 nodes.

### WP5 — SD journaling + readback scoring (3d)
Per-node per-tick log: `tick, snapshot_hash, intent, decision` to microSD, `planner_simulation` tag. Korvo pull + byte-for-byte verify + scorer.
- **Accept:** 10min @10Hz writes without drop (>6000 records); power-cycle → readback SHA matches; `tools/score.py` outputs commit/abstain/false-commit counts in <10s.

### WP6 — Host simulation twin (4d)
Bit-identical fixed-point twin on host (C++/Python) for WP1+WP2+WP4 logic. Not timing/render.
- **Accept:** host vs Korvo 1000-tick hash match for all WP0 seeds; twin runs 10× faster than real-time; used as golden reference for WP4/WP5 tests.

### WP7 — Fleet integration 16+1 (5d)
Full loop: Korvo ticks → broadcast → 16 panels interpolate/render/decide → intents back → journal. 5-min soak, link-loss injection.
- **Accept:** all 16 nodes stay synced <300ms for 5min; broadcast goodput <100kbps; zero desync requiring reboot; SD scores from all nodes collected.

### WP8 — GPU-offload fallback spike (3d, optional)
Only if WP7 fails render budget. Korvo renders 16× 64x64 views, streams as deltas. Contradicts fleet goal — measure only.
- **Accept:** decision memo with airtime math + demo that nodes become thin displays; default recommendation: do not ship.

## Python-first (before firmware)

Prototype in Python first: **WP1 kinematics, WP2 codec, WP4 decision table, WP6 twin + scorer.** ~6d, unblocks determinism + experiment design without hardware.
Firmware-only (do not Python-prototype): WP3 frame timing/PSRAM/SRAM, WP5 SD throughput, WP7 contention/retries, 10Hz jitter.

## Key risk

392B snapshot forces transport change. If ESP-NOW v2 not uniform or Wi-Fi AP contention spikes, fallback to 3-frame fragment + input-delay buffer 200-300ms. Decide in WP2 or WP3/WP7 slip.
