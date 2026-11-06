# Distributed flight simulator on the 16-panel fleet — design and feasibility

Date: 2026-11-07. Status: design/feasibility analysis only; nothing here is built or claimed as running. It proposes how to turn the panels' pregenerated state animations into a real distributed flight simulator in a shared virtual world, and evaluates the GPU-offload fallback.

## 0. Grounding: what exists today

| Fact | Source in this repo |
|---|---|
| 16 nodes A1-D4, each a Waveshare ESP32-S3 (N32R16: 32 MB flash, 16 MB PSRAM) driving one P2.5 64x64 RGB LED panel (160x160 mm), microSD per node, onboard mic / SHTC3 / QMI8658 IMU / PCF85063 RTC | `docs/hardware.md` |
| Korvo controller: ESP32-S31, 16 MiB flash, 16 MiB PSRAM, 800x480 touch display; standalone host for fleet control, planner, learning lab, archives | `firmware/korvo-monitor/README.md` |
| Panels today run *scripted display theatre*: `recon::scene(config, elapsed, i)` in `firmware/shared/recon/model.h` is a pure function of `(Config{run, seed, seconds, scenario, goal}, elapsed_ms, node_index)`. Every node derives the same 30-state script (`HOLD/SCAN/SEEN/SHARE/.../TAKEOFF`, sensor enum `CAM/WH/BH/NV/IR`) from `hash(seed, ...)` / `mix()` with no radio input. The header says so: "Scripted display theatre only. No navigation, inference or actuator outputs." | `firmware/shared/recon/model.h:1-2,73-141,243-397` |
| A first-person world renderer already exists on-node: `world::render()` raycasts a procedural ground plane per pixel (rows 8-49 x 64 px), projects peer aircraft as sprite markers, and recolours by sensor mode (`Cam/Night/WhiteHot/BlackHot/IR`, BlackHot = palette inversion) | `firmware/node-platform/include/world_render.h:68-130` |
| `mission_world::render()` already builds a 16-peer list per node per frame from `recon::Runtime::frame(now, id)` and feeds `world::render()` — i.e. all 16 poses are *already computed on every node*, just from the script instead of a live simulation | `firmware/node-platform/include/mission_world.h:27-39` |
| Management wire format: `flockwire` frames, `Header=40 B, Tag=32 B (HMAC), MaxPayload=160 B, MaxFrame=232 B`, kinds `Poll/Health/Open/Challenge/Begin/Data/Commit/Ack/SdRequest/SdReply/Mission/MissionReply`, per-node HMAC-SHA256 challenge-response with replay protection, keys generated at first (wired) flashing, never transmitted | `firmware/shared/commissioning/wire.h:5-6`, `docs/architecture.md` |
| ESP-NOW is already the node link transport (`esp_now_init`, broadcast peer + per-peer send in `node_link.cpp` / `network.cpp`); Wi-Fi is the commissioner/Korvo management route | `firmware/node-platform/src/node_link.cpp`, `firmware/node-platform/src/network.cpp:6,27-91` |
| Korvo owns simulation clocks and world state today; it creates planner journals tagged `planner_simulation`, pushes per-unit copies to panel SD and verifies them by byte-for-byte readback | `firmware/korvo-monitor/README.md`, `docs/judging/physical-execution-map.md` |
| Explicit non-claims: no on-node inference/learning is claimed; every scored decision trace so far is planner-simulation replay; the proposed bridge is a labelled wall-replay plus a future *panel-policy canary* whose decisions are journaled from the nodes themselves. Prerequisites already named: fleet clock authority (residual R5, SNTP configured but not started), per-node link-state journaling (R4), pre-registered canary plan | `docs/judging/physical-execution-map.md:21-53`, `docs/architecture.md` |
| The Kulira trust series (15 pre-registered, seeded lab-simulation experiments, simulation only, no hardware/radio/on-node inference) established the experiment discipline this design must inherit: admission by provenance (`direct_verified` only may decide a commit), strict commit / abstain on close calls, learned modality trust, seeds as the replication unit, holdout discipline | `docs/experiments/kulira-trust-series.md` |

Two consequences follow. First, the hard part is not drawing: a per-node first-person renderer and a 16-pose scene loop already exist and already run on the ESP32-S3. The hard part is replacing the *script as the source of truth* with a *live simulation as the source of truth* without breaking the experiment properties (provenance, determinism, journaling, management/experimental traffic separation in `docs/architecture.md`). Second, any design that moves rendering or deciding off the nodes contradicts the fleet's reason to exist (see Section 5).

### Hardware envelope used for all estimates below

- Node MCU: dual-core Xtensa LX7 @ up to 240 MHz, 512 KB SRAM, plus 16 MB octal PSRAM on the N32R16 module; single-precision FPU ([ESP32-S3 datasheet, Espressif](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf)).
- Frame buffer: 64x64 x RGB565 = 8,192 B. Double-buffered = 16 KB — trivially fits SRAM; no frame ever needs PSRAM bandwidth.
- ESP-NOW: connectionless vendor-specific action frames, default 1 Mbps PHY rate; v1.0 max payload 250 B, v2.0 max payload 1,470 B; v2 receivers accept both, v1 receivers truncate/discard >250 B ([ESP-IDF ESP-NOW reference, Espressif](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/network/esp_now.html)). The existing `flockwire` budget is stricter (160 B payload) because 72 B per frame goes to header + HMAC tag.
- Wi-Fi/UDP: the fleet already associates nodes for management; a conservative unfragmented UDP payload is ~1,200 B (under a 1,500 B MTU minus IP/UDP headers). Practical shared-cell goodput for 17 ESP-class stations on one 2.4 GHz AP is a few Mbps, not the PHY rate; all budgets below stay under ~1.5 Mbps payload so this is not the binding constraint — airtime contention and retries are.

## 1. Simulation partitioning

### 1.1 The simulated world (minimal, deliberately small)

One shared world, sized to what 16 quadcopters and a 64x64 view need:

- Coordinates: local flat world, +X east / +Y north / +Z up (already the convention in `world_render.h:8`), world extent ~480x480 m so the existing procedural terrain cells (24 m hash cells, `world_render.h:69-72`) tile it ~20x20 times.
- Entities: 16 aircraft. Per-aircraft authoritative state, 24 B compact form (the sync unit used in all math below):

  | Field | Encoding | Bytes |
  |---|---|---|
  | id + state enum + sensor mode | packed (`recon::State` is already `uint8_t`, `model.h:9-41`) | 2 |
  | position x, y, z | 3 x int16 fixed-point, 0.1 m steps (+/-3.2 km range) | 6 |
  | velocity vx, vy, vz | 3 x int16, 0.05 m/s steps | 6 |
  | heading, pitch, roll | 3 x int16, 0.01 deg steps | 6 |
  | tick/sequence low bits + flags (airborne, friendly, stale) | | 2 |
  | battery/health + link age | 2 x uint8 | 2 |
  | **Total per aircraft** | | **24** |

  Full snapshot = 16 x 24 B = **384 B** + ~8 B header (run id, tick, seed/cycle) = **392 B**. A float32 variant (9 x float32 + 4 B misc = 40 B/entity, 648 B snapshot) is carried as an upper bound; the fixed-point form is preferred (see Section 3 on determinism).
- Non-aircraft world state: none dynamic in v1. Terrain, targets and the three fixed sighting points (`world_render.h:79`) are procedural from the seed — they cost zero sync bytes, exactly as `recon::hash(seed, cycle, i)` costs zero bytes today. Dynamic events (target appears, link disrupted, modality betrays — the Kulira vocabulary) are director-issued event records, a few per minute, not per-tick state.
- Physics: kinematic quadcopter, not a flight-dynamics model. Per tick per aircraft: integrate velocity toward a commanded velocity (first-order lag), add drag and a turn-rate limit, integrate position, clamp to world bounds and a floor/ceiling. ~50-100 flops per aircraft. Sixteen aircraft plus O(n^2)=256 pairwise separation checks is well under 0.1 ms per tick on one 240 MHz core. Aerodynamic fidelity (rotor wash, ground effect, battery sag curves) is out of scope and buys nothing at 64x64.

### 1.2 Option A — full world replica per node (deterministic lockstep)

Every node holds the entire world and steps it identically. The radio carries only *inputs* (intents), never state:

- Per-node input per tick: commanded velocity/heading delta + discrete action (sensor switch, claim/share/check — the existing `Scene` vocabulary) ~ 4 B. All 16 inputs = 64 B + header ~ 72 B/tick — fits one `flockwire` frame (160 B payload) or one ESP-NOW v1 frame.
- Simulation tick 10 Hz with a 2-3 tick input-delay buffer (200-300 ms) to absorb broadcast jitter.
- Bandwidth: one aggregated input frame per tick if a collector (Korvo or a rotating leader) gathers and rebroadcasts them: 72 B x 10 Hz = 720 B/s = **5.8 kbps** broadcast. If instead every node broadcasts its own input (no collector): 16 x ~24 B on-air frames x 10 Hz = **160 pkt/s**, same payload total, 16x the contention (see Section 1.5).

Strengths: lowest bandwidth; every node provably computes the whole world (strongest form of the "nodes compute" claim); replay is trivial (Section 3).

Weaknesses, and they are decisive on this radio:

1. **Reliability.** Lockstep diverges permanently if any node misses any input. ESP-NOW broadcast is unacknowledged; the current code has no sim reliability layer. Lockstep therefore needs ACK/repair (per-tick input bitmaps, retransmit of missing inputs, stall when incomplete) — i.e. you must build reliable ordered broadcast over ESP-NOW before you can build the sim. That is the real project.
2. **Determinism.** All 16 nodes plus the host twin must produce bit-identical state from identical inputs. Today's model code is float-heavy (`std::sin/cos`, `float` physics in `model.h`). Same binary on same silicon is *likely* bit-identical in practice, but "likely" is not a journal-grade claim, and the Korvo (ESP32-S31) and host twins are different toolchains/libm. Lockstep done properly forces a fixed-point (or strictly ordered IEEE, no-fast-math) simulation core — a rewrite of the motion code, not a reuse of it.
3. **Late join / desync recovery** requires full-state checkpoint transfer anyway (384 B — cheap) plus a hash-chained resync protocol, and a single diverged node stalls or forks the fleet experiment until repaired.

### 1.3 Option B — director-authoritative world, per-node local rendering (recommended)

The Korvo is the single authority. It steps the world at a fixed tick; nodes are renderers + policy/input sources + witnesses:

```
        inputs/intents (unicast, per-node key)         snapshot (broadcast, run-scoped key)
 node ---------------------------------------> KORVO (authoritative sim, tick T)
 node <---------------------------------------  snapshot(T) = 16 x 24 B entities + events
 node: interpolate/extrapolate snapshot(T-1..T) at render rate, step local
       policy for next intent, journal (input, snapshot hash) to SD
```

- Tick rate: **10 Hz authoritative tick** (Section 1.4), nodes render at 20-30 fps by interpolating between the last two snapshots and dead-reckoning (velocity extrapolation, capped at ~300 ms) past the newest one. The existing `world::Runtime` already implements the render-side pattern: it quantises to 500 ms fixtures, marks samples `Live/Stale/Resync` after 1,500 ms, and blends on resume over 750 ms (`world_render.h:44-67`) — the staleness vocabulary carries over directly, with the fixture replaced by snapshots.
- Node uplink per tick: intent 4 B + policy event flags, ~16 B in a `flockwire`-style frame. Unicast to the Korvo, authenticated with the existing per-node HMAC — this is the one place the sim touches identity, and it aligns with Kulira experiment 2 (Policy D: verified-origin admission; 0 forged-origin commits) in `docs/experiments/kulira-trust-series.md`: the director can *prove who sent an intent*, while still treating the intent's *truth* as experiment data, never as authority (`docs/architecture.md`: "Authentication answers who sent a message, never whether its claim is true").
- Director downlink: one broadcast snapshot per tick (392 B). The broadcast cannot be per-node-HMAC'd (16 different keys); options: (a) a run-scoped group sim key, issued by the Korvo over the existing authenticated unicast channel at run start and rotated per run — compromise of the group key forges *sim snapshots for one run only*, never management authority, provided sim and management stay separate traffic classes as `docs/architecture.md` mandates; (b) director signs a hash of the snapshot and rotates a truncated tag through the unicast channel. Option (a) with strict class separation is sufficient; the sim channel must never be able to trigger OTA, SD, or maintenance kinds (`wire.h` kinds stay management-only, reached only via the existing challenge flow in `node_link.cpp`).
- Loss behaviour: a missed snapshot costs one 100 ms interpolation gap; the next snapshot heals completely because snapshots are full-state, not deltas. This is the decisive advantage over lockstep on an unacknowledged broadcast radio: **no reliability layer is required for correctness**, only for smoothness (optional snapshot redundancy: repeat each snapshot twice, 2x bandwidth, still trivial — see tables).
- Compute: the Korvo steps 16 kinematic aircraft — negligible next to its current planner/lab load (`firmware/korvo-monitor/README.md`: it already "owns the simulation clocks and world state"). Nodes do *not* step the world; they step only their own policy (the canary, Section 3) and their renderer. The honest claim becomes "director-authored world, node-rendered, node-decided intents" — weaker than lockstep's claim, and it must be labelled as such per `docs/judging/physical-execution-map.md`.

A hybrid is possible later — director-authoritative with *node-local prediction of own ship only* (the node predicts its own aircraft between snapshots, director corrects) — which cuts perceived latency for the node's own view without lockstep's fleet-wide determinism burden. It complicates the journal (predicted vs corrected positions must both be logged) and is not needed at 10 Hz / 64x64.

### 1.4 Tick rate choice

| Tick | Input-to-photon latency (intent applied) | Snapshot bandwidth (broadcast) | Verdict |
|---|---|---|---|
| 5 Hz | 200-400 ms (tick + interp buffer) | ~2 KB/s | Flyable for loiter/survey choreography; sluggish for claim/contest interactions (the 2 s interaction beats in `model.h:318-359` still work) |
| **10 Hz** | **100-250 ms** | **~4 KB/s** | **Recommended.** Matches the 100 ms scale of existing scripted beats; radio load trivial; interpolation hides it |
| 20 Hz | 50-150 ms | ~8 KB/s | Affordable in bandwidth, but 320 pkt/s in decentralised variants and 2x wakeups buy little at 64x64 theatre viewing distance |

Render rate is independent: 20-30 fps locally (Section 2), decoupled from tick by interpolation — the same decoupling `world::Runtime::tick()` already does between its 500 ms fixtures and the panel refresh.

### 1.5 Bandwidth estimates, 16 nodes (payload bytes, before radio framing)

Snapshot 392 B (fixed-point) / ~648 B (float). ESP-NOW v1 usable 250 B/frame; `flockwire` usable 160 B/frame; ESP-NOW v2 / UDP usable ~1,200 B/frame.

| Scheme | Frames/tick | 5 Hz | 10 Hz | 20 Hz | Pkt/s @10 Hz |
|---|---|---|---|---|---|
| B: director broadcast snapshot, ESP-NOW v2 or UDP-broadcast | 1 | 15.7 kbps | 31.4 kbps | 62.7 kbps | 10 |
| B: director broadcast snapshot, ESP-NOW v1 (250 B) | 2 | 31.4 kbps | 31.4 kbps | 62.7 kbps | 20 |
| B: director broadcast snapshot, `flockwire` framing (160 B) | 3 | 31.4 kbps | 31.4 kbps | 62.7 kbps | 30 |
| B: director **unicast** snapshot x16 (UDP) | 16 | 251 kbps | 502 kbps | 1,004 kbps | 160 |
| A: lockstep, aggregated inputs via collector (broadcast) | 1 | 2.9 kbps | 5.8 kbps | 11.5 kbps | 10 (+16 uplink) |
| A-prime: every node broadcasts own state/input (no director) | 16 | 30.7 kbps | 61.4 kbps | 122.9 kbps | 160 @10 Hz, 320 @20 Hz |

Payload kbps are identical across framings of the same scheme; v1/`flockwire` multiply *frame count*, hence contention and per-frame overhead (40 B header + 32 B tag in `flockwire`; ~24 B MAC/action-frame overhead in raw ESP-NOW), not payload. Add ~30-70% on-air overhead at these small sizes.

Reading of the table:

- **Broadcast is the whole game.** One Korvo broadcast serves all 16 nodes; unicasting the same snapshot costs 16x and at 20 Hz crosses 1 Mbps payload on a shared 2.4 GHz cell with 17 stations — still survivable, but pointless. ESP-NOW broadcast (no AP association needed, works when Wi-Fi management is busy or down) is therefore the right sim downlink; UDP broadcast/multicast is the fallback if ESP-NOW v2 is unavailable on the Korvo's ESP32-S31 stack and fragmentation is to be avoided entirely.
- **Decentralised per-node broadcast (A-prime)** is the only scheme whose packet rate (160-320 pkt/s of small frames, unacknowledged, colliding) can hurt: at 20 Hz, 320 pkt/s with CSMA backoff on one channel will show loss bursts exactly when all nodes manoeuvre together. It also has no authority to journal against (Section 3). Not recommended as the primary scheme; it remains interesting as a *Kulira experimental condition* (peer traffic is class 4 in `docs/architecture.md` — "only the channels an experiment grants").
- ESP-NOW vs UDP for the downlink is otherwise a wash at these rates. ESP-NOW wins on: no AP dependency, lower and more stable latency (connectionless action frames; the fleet already runs it), and consistency with the LilyGo recovery precedent. UDP wins on: 1,200 B unfragmented snapshots, host tooling visibility, and no 250 B v1 trap. **Recommendation: ESP-NOW v2 if the S31 Korvo IDF enables it, else ESP-NOW v1 with 2-frame snapshots, sequence + tick in each fragment; keep a UDP build variant for host-in-the-loop debugging.** Either way the sim wire is a *new* experimental-class format; do not overload `flockwire` management kinds for it.

Wi-Fi management coexistence: snapshots at 10-30 pkt/s are noise next to health polling and journal delivery, provided bulk/journal traffic stays scheduled so it "cannot starve the other classes" (`docs/architecture.md`, traffic class 3) and journal pushes do not run during a scored sim run (see Section 3).

## 2. What each node renders locally, and the compute budget

Each panel is one aircraft's station. It never draws the God's-eye wall view (that is the Korvo's 800x480 screen and the host tooling); it draws *what its own quadcopter sees*, from its own interpolated pose:

1. **Scrolling terrain (already built).** `world::render()` casts one ray per pixel (64 wide x 42 tall view band) through the camera basis from heading/pitch/roll, intersects the ground plane, and samples procedural terrain — `terrain(x, y)` is a seeded hash over 24 m cells (`world_render.h:69-72`), so the ground scrolls, rotates and banks correctly as the aircraft moves, with zero map storage and zero sync cost. Sensor modes recolour the same geometry: daylight palette, night-vision greens, white-hot/black-hot greys with inversion, IR greens (`world_render.h:107-116`) — the direct descendants of `recon::Sensor {CAM, WH, BH, NV, IR}` in `model.h:59`.
2. **Peer sprites (already built).** `world::sightings()` projects the other 15 aircraft into the view, draws in-view peers as markers and out-of-view peers as edge arrows with `R` (rear) labels, caps at 3 labelled markers + a `+N` overflow count (`world_render.h:76-102`). In the sim these positions come from the snapshot instead of `world::fixture()` — the projection, occlusion-free sprite logic and label collision avoidance are unchanged.
3. **HUD and state theatre (already built).** Heading tape / north arrow, altitude, sensor tag, `SURVEY/LOITER/SHARE/CHECK` phase label, `STALE/RESYNC/SIGNAL LOST` freshness states (`world_render.h:118-130`), composited with the `recon::render()` overlay that already draws the 30-state script theatre (`mission_world.h:32-37`). The sim replaces the script's *cause*; the visual vocabulary — including the Kulira states `DOUBT/CHECK/SHARE/YIELD/PRIORITY` — is the presentation layer the audience already reads.
4. **Own-ship policy view (new, small).** The node's policy (Section 3) consumes the same snapshot the renderer consumes, plus its private sensor model (e.g. a degraded/noisy or modality-betrayed view of contacts, per the Kulira graded-sensing/modality-betrayal experiments). The *rendered* view should be the policy's view, not the director's truth — that gap is the experiment. Director truth stays sealed, exactly as today (`docs/architecture.md` traffic class 4).

### Compute budget split (per node, ESP32-S3 @ 240 MHz)

Measured anchor: the existing firmware already instruments this loop — `world_timings[256]`, `world_count`, `world_max_us` in `firmware/node-platform/src/display.cpp` — so every figure below is checkable on hardware before any sim code is written; treat them as budgets to verify, not measurements.

| Task | Rate | Estimated cost | Share of one core |
|---|---|---|---|
| Sim step (director scheme: interpolate 16 entities; lockstep: step 16) | 10 Hz tick, render-rate interp | <0.1 ms/tick (kinematics + 256 pair checks) | <1% |
| Own-ship policy (waypoint steering, trust/commit rules — integer comparisons over <=15 contacts) | 10 Hz | <0.1 ms/tick | <1% |
| World render: 2,688 raycasts (hash terrain + basis dot products), palette lookup | 20-30 fps | ~1-3 ms/frame (est. 100-300 cycles/px) | ~5-10% @30 fps |
| Recon overlay, HUD text, sprite projection (<=15 peers) | per frame | <0.5 ms | ~2% |
| Snapshot RX parse + intent TX (ESP-NOW callbacks, queue) | 10 Hz | <0.2 ms/tick | <1% |
| HUB75 panel refresh (DMA/ISR, existing driver) | continuous | hardware DMA + ISR load, already borne today | existing |
| SD journal append (batched, Section 3) | 1 flush/s | ~1-5 ms/s in bursts (SDMMC) | ~0.5% |
| Management, health, sensors, audio (existing) | existing | already borne today | existing |

Total new load is roughly **10-15% of one core**; the second core and the existing task split remain headroom. Conclusions:

- **Rendering dominates; simulation is noise.** At 64x64 there is no compute argument for moving either off the node. The split is ~85% render / ~5% sim+policy / ~10% network+journal/system within the new code.
- The real rendering choice is *style*, not feasibility: (a) the existing first-person flat-terrain raycast (~2,688 px) at 30 fps; (b) a 2D top-down scrolling map (translate world XY into panel XY, blit aircraft sprites + terrain tiles) which is *cheaper* — a few hundred sprite/tile writes per frame, no per-pixel ray — and reads better as a shared-world view across the 4x4 wall; (c) pseudo-3D heightfield (Section 6, stretch). All three consume identical sync state; the renderer is interchangeable per node or per run.
- Memory is a non-issue: world state 384 B, two frame buffers 16 KB, terrain procedural, sprites generated. Even a 480x480 m tile cache at 1 byte/cell is 230 KB in PSRAM if a future renderer wants one.

One caution carried from the current code: `world::authored()` / `fixture()` poses are smooth trigonometric paths (`world_render.h:37-42`). The sim pose will be *less* smooth (10 Hz snapshots), so interpolation quality — not raw rendering — is what will make it look like flight rather than teleporting. Budget the interpolation/extrapolation code review accordingly; the `Live/Stale/Resync` freshness labels must reflect snapshot age honestly, as they already do for fixtures.

## 3. Deterministic replay and journaling implications

Today's contract (`firmware/korvo-monitor/README.md`, `docs/judging/physical-execution-map.md`): the Korvo creates journals tagged `planner_simulation`, pushes per-unit copies to panel SD, and verifies every byte by readback; scoring is offline and deterministic on the lab host (`tools/fleet-score`); the seed (episode) is the replication unit. The sim must strengthen, not dilute, that contract — and it finally enables the *panel-policy canary* the execution map calls the "actual closed loop": a policy executing on the nodes, "journaled from the nodes themselves."

Design:

1. **Logical clock first.** Residual R5 is explicit: controller SNTP is configured but not started and cross-device timestamps are provisional. The sim must not depend on wall time. The director tick (uint32, 10 Hz, monotonic per run) is the only clock the sim, the journal and the scorer share — the same role `elapsed_ms` plays in `recon::scene()` today. Wall timestamps are recorded as untrusted metadata. This also defers (does not solve) R5; say so in run reports.
2. **Journal inputs and hashes, not frames.** Per run, the Korvo journal header records: run id, seed, world/scenario/goal config (the existing `recon::Config` fields), sim wire version, tick rate, initial state, and the hash of the sim binary/policy builds. Per tick it records only: the 16 intents actually applied (16 x 4 B), any director events, and a 4 B state hash (the `recon::hash/mix` family in `model.h:132-141` is the in-repo precedent; a CRC32 or truncated BLAKE2s over the 384 B snapshot is the journal-grade version). Full snapshots are written only as keyframes every 50 ticks (5 s). Cost: ~70 B/tick = 700 B/s ~ **2.5 MB/hour** on the Korvo SD — trivial — versus 5 KB/s for naive full-state journaling, which is also affordable but buys nothing.
3. **Two replay modes, honestly labelled.**
   - *State replay* (always possible): re-render any run from keyframes + snapshots. Bit-exact by construction; this is the wall-replay mode, and must be captioned as replay, per the execution map's labelling requirement.
   - *Re-simulation replay* (the scored mode): re-step the world from (seed, initial state, journaled intents) and check the state hash every tick. This is only sound if the sim core is deterministic — hence the fixed-point snapshot encoding in Section 1.1 and a sim core that avoids transcendentals in the step (heading trig belongs in the *renderer*, which may float freely because it does not feed back into state). If the fleet ever runs the float variant, re-simulation replay degrades to approximate and must be reported as such; the hash-per-tick journal makes that degradation *detectable* rather than silent, which is the point of journaling hashes at all.
4. **Node-side journals are the canary evidence.** Each node appends to its own SD: intents it sent (with tick), snapshot hashes it received, its policy's discrete decisions (claim/check/share/abstain — the Kulira commit vocabulary), and render freshness transitions. At ~10-20 B/tick batched to 1 flush/s this is <1 MB/hour/node. After a run, the existing verified-readback path collects them. Only these node-authored journals can ever support a claim of on-node decision-making; a Korvo journal alone proves, in the README's words, "storage, not learning on each panel." Link-state per tick (snapshot age, missed-tick bitmap) simultaneously closes residual R4 (per-node link-state journaling) for sim runs.
5. **What this does to Kulira experiments.** The trust series was simulation-only throughout (`docs/experiments/kulira-trust-series.md`: "no hardware, no radio, no on-node inference"). The sim turns the same pre-registered, seeded designs (relay, collusion, modality betrayal, feedback delay) into *embodied* variants where provenance, delay and loss are physical rather than modelled. That is a new experiment family requiring new pre-registrations and fresh evaluation seeds (the series already flags its seeds 100-109 as design-exposed); it does not retroactively upgrade any existing result. Adversarial injection (Kulira `disrupt/spoof/deceive/relay` in `tools/kulira-core`) maps cleanly: spoofed snapshots test the group-key boundary, relayed intents test Policy D admission, delayed snapshots test the feedback-delay findings — all on the experimental channel only, never on management traffic.

## 4. GPU-offload alternative: host/Korvo renders, panels display streams

The fallback: render each panel's view centrally (lab host GPU, or nominally the Korvo) and stream pixels to panels that only decode and push to the HUB75. Panels become thin terminals.

### 4.1 Bandwidth math (per panel = one distinct 64x64 first-person view)

Raw frame = 64x64 x 2 B (RGB565) = **8,192 B**.

| Encoding | Bytes/frame (est.) | @10 fps per panel | @15 fps per panel | @30 fps per panel | x16 panels @15 fps | Encode/decode load |
|---|---|---|---|---|---|---|
| Raw RGB565 | 8,192 | 655 kbps | 983 kbps | 1,966 kbps | **15.7 Mbps** | None; pure transport. 33 ESP-NOW v1 fragments/frame/panel |
| MJPEG (64x64 JPEG, q~70; JPEG header dominates at this size) | ~1.5-3 KB | 120-240 kbps | 180-360 kbps | 360-720 kbps | **2.9-5.8 Mbps** | Host: 240 JPEG encodes/s of tiny frames — trivial for a host GPU/CPU. Korvo (ESP32-S31, no JPEG hardware assumed): 240 software encodes/s is not credible alongside its host duties. Node: software JPEG decode 64x64 ~5-15 ms/frame on LX7 |
| Delta tiles (8x8 px tiles = 64 tiles x 128 B raw + tile bitmap) | static HUD: ~0.5 KB; **scrolling terrain: ~6-8 KB** | 40-640 kbps | 60-960 kbps | — | **1-15 Mbps, scene-dependent** | Cheap codec both ends, but see below |

(For scale, published MJPEG references put 320x240 at 8-20 KB/frame; a 64x64 frame has 1/18.75 the pixels but a fixed ~0.6 KB JPEG header/quantisation overhead, hence the 1.5-3 KB estimate — the header, not the pixels, is the cost at panel size. Delta tiles fail precisely in the flight case: when the terrain scrolls under the aircraft, essentially every tile changes every frame, so "delta" degenerates to raw with bitmap overhead. Deltas only win for near-static screens — i.e. for the theatre the project already does locally for free.)

Transport reality check:

- **Over ESP-NOW: infeasible at video rate.** Even MJPEG at 15 fps is 16 panels x 15 fps x ~2 KB = 480 KB/s of payload that must be *unicast* (each view differs), fragmented into ~8-12 ESP-NOW v1 frames per JPEG — roughly **2,000-2,900 small frames/s** on one 1 Mbps-default-rate connectionless channel shared with management. It collapses.
- **Over Wi-Fi/UDP: feasible as transport, fragile as a system.** 2.9-5.8 Mbps payload to 16 stations on one AP cell is within reach, but it is 16 independent unicast video streams competing with health, journal and OTA traffic, with head-of-line loss showing as torn/frozen panels rather than graceful `STALE` states. A single AP retry storm freezes the wall in a way the local-render design cannot.
- **Korvo as renderer is the weakest variant.** The Korvo is itself an ESP32-class device (16 MiB PSRAM, no GPU; `firmware/korvo-monitor/README.md`). It can raycast one 800x480 screen for its own display; rendering + JPEG-encoding 16 distinct 64x64 views at 15 fps is a host job. "GPU-offload" therefore honestly means "lab host with a GPU renders" — which reintroduces the external host the standalone Korvo architecture was built to remove.

### 4.2 Latency math (per frame, streamed vs local)

| Stage | Streamed (host render, Wi-Fi) | Local render (Option B) |
|---|---|---|
| Sim state available | 0-100 ms (tick) | 0-100 ms (tick) |
| Render | 1-5 ms (host GPU, batched) | 1-3 ms (node) |
| Encode (MJPEG) | 1-5 ms | — |
| Transport + queueing, 16 streams | 10-50 ms (contention-dependent, unbounded tail) | 2-10 ms (one 392 B broadcast, all nodes at once) |
| Decode (JPEG, node LX7) | 5-15 ms | — |
| HUB75 push | ~5 ms | ~5 ms |
| **Total, typical / tail** | **~50-120 ms / 200 ms+ under load** | **~110-250 ms intent-to-photon, but frame-to-photon after state arrival ~10 ms and immune to stream contention** |

The streamed design's latency is not catastrophic; its *variance* and its failure modes are. Local rendering degrades to interpolation and honest `STALE` labels; streaming degrades to frozen or torn video.

### 4.3 Why it breaks the "nodes compute" experiment goal — and where it is still the right tool

- The project's central instrument claim is that each panel is an independent agent body that "senses, stores state, renders, and sounds locally" (`docs/architecture.md`), and the execution map's whole purpose is refusing to let the wall imply panel cognition that happened elsewhere (`docs/judging/physical-execution-map.md`). GPU-offload makes that implication false by construction: panels would display host decisions with host rendering, and no journal could ever be "journaled from the nodes themselves." It forecloses the panel-policy canary permanently, not temporarily.
- It also inverts the fleet's resilience invariants: experiments must "continue if a remote or browser disconnects" (`docs/architecture.md`); a streamed wall dies with the host/AP, while a snapshot-fed wall flies on through a host disconnect at `STALE`-then-hold.
- **Where it does suit: the wall as a display, not as a fleet.** If the goal is a single 256x256 tiled mosaic image (one render split into 16 tiles of 64x64), a wall backdrop, a museum attract loop, or showing a heavyweight visualisation (e.g. a GPU simulation far beyond node physics, SAM-style segmentation overlays) that no one claims the nodes computed — then streaming is simpler and better: one render, one encode (~15-30 KB/frame at 256x256), tile-split to panels at 10-15 fps for ~1.8-3.5 Mbps total, explicitly labelled as host-rendered display, exactly like the proposed labelled wall-replay. That is a legitimate *presentation* mode. It is not a flight simulator *on* the fleet, and must never be captioned as one.

## 5. Cross-cutting constraints inherited from the current architecture

- **Traffic classes stay separate** (`docs/architecture.md`): management (per-node HMAC, challenge-response) / observation-action / bulk / experimental peer traffic. The sim downlink is observation/action; sim uplink intents are experimental unless admitted under Policy D provenance; journal bulk moves only between runs. The sim group key must be cryptographically incapable of minting management authority.
- **Per-node keys remain private and untransmitted**, generated at wired first flashing; the sim adds exactly one new secret class (run-scoped group sim key, issued over the existing authenticated channel, rotated per run, worthless after it) and must say so in the run's provenance record.
- **Brightness/power invariants unchanged**: 25% default, 50% ceiling, everywhere (`docs/architecture.md`) — a sim that needs brighter panels to be readable is a failed design at this panel size.
- **Deterministic seeds**: the seed stays the replication unit; agents in one run are correlated, not independent samples. Sixteen panels flying one world is *one* episode for statistics, a fact the scorer and any future pre-registration must respect.
- **The Korvo stays the standalone host**: no design element may require a browser or lab host to keep a run alive. The host twin exists for re-simulation scoring and debugging (UDP variant), never in the live loop.

## 6. Phased feasibility verdict

| Phase | Scope | Feasibility | Basis |
|---|---|---|---|
| **Now: dynamic 2D top-down shared world** | Korvo-authoritative kinematic sim @10 Hz (Section 1.3), ESP-NOW broadcast snapshots (392 B), per-node top-down or existing first-person rendering, node policies issuing intents over authenticated unicast, tick-hash SD journaling on Korvo + nodes | **Achievable with current hardware and mostly current code.** New work is the sim core, the sim wire format, interpolation, and journal plumbing — weeks-scale firmware work, no new hardware, no radio heroics (31 kbps broadcast) | Physics/render budgets in Sections 1-2 are 1-2 orders of magnitude inside the envelope; `world_render.h` / `mission_world.h` already prove the render path on-node |
| **Next: the panel-policy canary** | Node-local policies (trust/commit/sensor-degradation rules from the Kulira series) decide intents on-node; node-authored SD journals collected by verified readback; pre-registered canary with promotion gates | **Achievable, gated on process not technology**: needs the fleet clock decision (tick-as-clock, R5 explicitly deferred), per-node link-state journaling (R4, delivered by the sim journal), and the pre-registration discipline of `docs/experiments/kulira-trust-series.md` | This is the execution map's own stated bridge (`docs/judging/physical-execution-map.md:47-52`); the sim is its missing substrate |
| **Stretch: pseudo-3D per node** | Heightfield terrain (replace flat-plane `terrain()` with seeded elevation + shading/fog), scalable peer sprites with distance attenuation, weather/link-degradation visualisation, own-ship prediction | **Plausible at reduced rate (15-20 fps).** Per-pixel cost rises ~2-4x (heightfield raymarch or precomputed tile rendering); still inside the render budget, but interpolation and sprite scaling at 64x64 will look coarse. Prototype behind the existing `world_max_us` instrumentation and let measured frame times decide | Follows the existing raycast structure; risk is aesthetic, not architectural |
| **Infeasible (do not attempt/claim)** | (a) Full 3D textured rendering per node at video rate (textured polygons, lighting, textured terrain at 30 fps on LX7 with HUB75 refresh); (b) deterministic fleet-wide lockstep over raw ESP-NOW broadcast without building reliable ordered broadcast first; (c) per-node streamed video (MJPEG/raw) as the *simulator* substrate, especially over ESP-NOW or from the Korvo as encoder; (d) any variant claiming on-node learning/inference from Korvo/host journals | **Infeasible or claim-invalid on this hardware/architecture.** (a) exceeds the fill/texture budget by orders of magnitude at useful fidelity; (b) fails on a single lost input frame; (c) fails the packet-rate math in Section 4.1 and the execution-map honesty test in Section 4.3; (d) is excluded by the repo's own non-claims until node-authored journals exist | Sections 1.2, 4, and `docs/judging/physical-execution-map.md:23-31` |

Recommended sequencing: build Option B top-down first (it is the smallest change that makes the world *shared and live*), keep the existing first-person renderer as a per-node view option from day one (it consumes the same snapshots), instrument frame times on hardware before committing to pseudo-3D, and treat GPU streaming strictly as a labelled presentation/replay mode for the wall — never as the simulator.

## 7. Open questions / risks

1. Does the ESP32-S31 Korvo's IDF configuration enable ESP-NOW v2 (1,470 B)? If not, the 2-frame v1 snapshot path is the baseline and must be soak-tested alongside health polling. (Verify against the pinned ESP-IDF 6.1 in `firmware/korvo-monitor/README.md`.)
2. Measured `world_max_us` on physical panels at the target render rate — the budget in Section 2 is an estimate until the existing instrumentation in `display.cpp` reports otherwise on hardware.
3. Group sim key issuance UX: run start already has a one-minute authenticated countdown precedent (`firmware/korvo-monitor/README.md`); key issue should ride it, but the failure mode "one node missed the key" needs a defined behaviour (node shows `NOLINK`, does not free-run).
4. Policy expressiveness vs journal size: discrete Kulira-style decisions journal compactly; any future continuous learned policy (e.g. distilled network) reopens the on-node inference claim and needs its own evidence bar, execution-map update, and power/thermal check at the 50% brightness ceiling.
5. Interference: the sim, journal delivery and OTA all share one 2.4 GHz environment; a pre-registered run protocol should freeze OTA/bulk during scored runs (traffic class 3 scheduling already requires the mechanism).

## Sources

Project files (this repository): `docs/hardware.md`; `docs/architecture.md`; `docs/judging/physical-execution-map.md`; `docs/experiments/kulira-trust-series.md`; `firmware/shared/recon/model.h`; `firmware/shared/commissioning/wire.h`; `firmware/node-platform/include/world_render.h`; `firmware/node-platform/include/mission_world.h`; `firmware/node-platform/include/recon_render.h`; `firmware/node-platform/src/display.cpp`; `firmware/node-platform/src/node_link.cpp`; `firmware/node-platform/src/network.cpp`; `firmware/korvo-monitor/README.md`.

External primary sources: [ESP32-S3 Series Datasheet (Espressif)](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf) — LX7 dual-core 240 MHz, 512 KB SRAM, PSRAM support; [ESP-IDF Programming Guide: ESP-NOW (Espressif)](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/network/esp_now.html) — connectionless action frames, 1 Mbps default rate, v1.0 250 B / v2.0 1,470 B maximum payloads and cross-version receive behaviour.
