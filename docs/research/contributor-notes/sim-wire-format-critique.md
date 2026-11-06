<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Reviewed by supervisor before use; not yet adopted. Adapt host/framing details to Korvo + flockwire before implementation. -->

## Critique: director-authoritative (Option B) is the only startable path

Agree with draft: **Option A (lockstep) is not buildable first.** It requires reliable ordered broadcast + bit-identical fixed-point sim + checkpoint/resync before any flight is seen. Option B degrades gracefully on loss because snapshots are full-state.

Blocking gaps in draft before firmware:

### 1. Missing failure modes

- **Radio coexistence:** Wi-Fi mgmt + ESP-NOW sim share one 2.4 GHz radio. No time-slice / channel / priority rule defined.
- **Snapshot > single frame:** 392 B snapshot does not fit `flockwire` 160 B payload nor ESP-NOW v1 250 B. No fragmentation / reassembly / drop-partial rule.
- **Clock with no authority:** R5 still open — SNTP configured, not started. No tick-to-wall mapping, no late/early snapshot rule, no Korvo crash / restart / tick-reset handling.
- **Director as SPOF / partition:** Korvo stall, reboot, AP loss. Nodes need defined hold / dead-reckon-cap / freeze + journal behavior, not indefinite extrapolation.
- **Version skew:** `recon::Config`, `recon::State`, renderer, sim core can diverge silently. No compat check.
- **Intent loss / duplication / reorder:** default-on-missing-intent undefined. Replay of old intent possible.
- **Event reliability:** target-appear / link-disrupted events are few-per-minute but state-changing. Broadcast-only loses them.
- **Journal pressure:** per-tick `(input, snapshot-hash)` to SD x 16 nodes. No full-disk, write-stall, torn-write, readback-verify rule.
- **Key-scope bleed:** run-scoped group sim key proposed. No issuance / rotation / revocation / separation rule to keep sim key from reaching `wire.h` mgmt kinds (Poll/Open/Commit/OTA/SD).
- **Render starvation:** HUB75 DMA + PSRAM + SD + RX contention on LX7. No frame-drop policy: drop render, never drop journal/seq accounting.
- **Late join / resync mid-run:** node reboot at tick `T+k`. No checkpoint + hash-chain catch-up.

### 2. Wire-format details needed first (freeze in spec, not code)

**Common header for all sim frames, distinct from mgmt `flockwire` kinds:**
- `sim_version:u8, sim_tick:u32 monotonic, run_id:u128, seed:u32, cycle:u16, sender:u8`
- `kind: SNAPSHOT_FRAG / INTENT / EVENT / RESYNC_REQ / RESYNC_REPLY`
- Journal `run_id + sim_version + seed` verbatim. Seeds are replication unit.

**SNAPSHOT (Korvo -> all, broadcast):**
- Define: `total_frags, frag_idx, tick, prev_tick_hash`. Fixed-point entity layout from §1.1 locked as v1; float32 banned for sync.
- Auth: run-scoped group key only, tag covers header+payload. Explicit: never accepted for mgmt.
- Loss: idempotent last-writer-wins. Missing frag = drop whole tick. Interpolate `T-1..T`, dead-reckon cap + `Live/Stale/Resync` thresholds carried from `world_render.h`, then freeze.

**INTENT (node -> Korvo, unicast):**
- Define: `base_tick, intent_seq per-node monotonic, 4 B command + flags`. Existing per-node HMAC, replay window.
- Loss: Korvo uses newest `intent_seq <= T-2`; missing = `HOLD + keep sensor`. Duplicates suppressed by seq. No NACK.

**EVENT (Korvo -> nodes, director-issued Kulira vocabulary):**
- Must be reliable: `event_id monotonic, apply_tick, payload`. Repeat in snapshots until acked via unicast bitmap or `RESYNC_REPLY`. Nodes journal `applied / skipped`.

**Versioning / falsification:**
- Pre-register: abort if mixed `sim_version`, tick rollback without new `run_id`, or snapshot-hash divergence between Korvo log and node logs for same `run_id+ticks`.

### 3. Ordering — do not interleave

1. **Clock + link journal (close R4/R5):** Korvo tick authority, node link-state logging, SD full/verify rule. No sim yet.
2. **Wire spec v1 frozen + host twin:** Korvo + host-only replay of snapshot/intent/event, hash-chained. Simulation-only.
3. **Snapshot broadcast harness:** Korvo emits empty ticks + frags; nodes log seq gaps, render nothing new. Gate for radio work.
4. **Node render from snapshot:** replace `recon::Runtime::frame()` source with interpolator; keep script as fallback file. No intents.
5. **Intent uplink:** unicast intents, Korvo applies, journal both sides, byte-readback like planner journals.
6. **Events + resync:** reliable events, late-join checkpoint transfer.
7. **Panel-policy canary only:** node-decided intents, journaled, labelled `director-authored world, node-rendered, node-decided intents`. No on-node inference claim.

### 4. Riskiest assumption + cheap test

**Riskiest:** Unacknowledged broadcast snapshots are *smooth enough* while nodes drive 64x64 HUB75, service Wi-Fi mgmt, and append to SD — with no reliability layer and with 392 B requiring multi-fragment per 100 ms tick.

**Cheap test (no physics, no renderer change):**
- Korvo broadcasts `tick_seq` frags at proposed tick rate. 2–3 nodes only, display on, SD journal on, Wi-Fi associated.
- Nodes append `(recv_tick, frags_seen, gap)` to SD. Vary: display on/off, SD on/off, Wi-Fi on/off.
- Pre-register falsifier: e.g. any sustained gap pattern that breaks interpolation cap / forces `Stale/Resync`, or any frag-partial that would require redesign to unicast or smaller tick. If failed, do not build sim — fix coexistence / fragmentation / rate first.
