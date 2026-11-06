# SIM Channel v1 Wire Spec — `director-authoritative`
**Pre-registered, simulated data only. `director-authored world, node-rendered, node-decided intents`.**
Separate from `flockwire` mgmt channel. Mgmt MTU 160B unchanged. **SIM MTU 160B** (fits ESP-NOW v1 250B with margin).

## 0. Separation + auth

* `SIM_MAGIC=0x53`. Mgmt parser drops `0x53`. Sim parser drops all `flockwire` kinds (`Poll/Open/Commit/OTA/SD`).
* Keys: `mgmt_key` (long-lived) vs `sim_key` (32B run-scoped, generated per `run_id`, distributed via mgmt `Commit`). **Never cross-accept.** Tag fail = silent drop, counter++.
* Tag: `TAG = HMAC-SHA256(sim_key, header||payload)[0:8]` LE, appended. Covers all except TAG itself.
* Radio rule (v1): Korvo tick is authority. 100ms tick: `0-60ms` SIM broadcast, `60-100ms` mgmt/unicast. Nodes never TX SIM except INTENT/RESYNC in unicast window. Drop render, never drop seq/journal accounting.

## 1. Common header (30B, all LE except `run_id` opaque)

| Off | Sz | Field | Value |
|---|---|---|---|
| 0 | 1 | `MAGIC` | `0x53` |
| 1 | 1 | `VERSION` | `0x01` |
| 2 | 1 | `KIND` | `1=SNAP_FRAG,2=INTENT,3=EVENT,4=RESYNC_REQ,5=RESYNC_REPLY` |
| 3 | 1 | `SENDER` | `0=Korvo,1-16=panel,0xFE=host-twin` |
| 4 | 4 | `TICK` | `u32` monotonic from 0, no rollback |
| 8 | 16 | `RUN_ID` | `u128` UUIDv4 per run |
| 24 | 4 | `SEED` | `u32` replication unit |
| 28 | 2 | `CYCLE` | `u16` Korvo boot count, tick resets only if `CYCLE++` + new `RUN_ID` |

Wire: `header(30) + payload(0..122) + tag(8) <= 160B`.

```c
typedef struct __attribute__((packed)) {
  uint8_t magic, version, kind, sender;
  uint32_t tick; uint8_t run_id[16]; uint32_t seed; uint16_t cycle;
} sim_hdr_t; // 30B
// static_assert(sizeof==30);
```

## 2. Frame layouts

### 2.1 SNAP_FRAG Korvo->all broadcast, 142B

Full state 392B fixed-point, **float32 banned**. `world[392]`: `0-7: tick u32, hiker_x i16 dm, hiker_y i16 dm (0x7FFF=hidden)` + `16x24B robots`. Per robot: `x i16, y i16 dm, heading u16 decideg, speed i16 cm/s, mode u8, flags u8, ack_seq u8, rssi u8, task_x i16, task_y i16, sensor u32, spare u32=0`.

Frag payload (104B):

| Off (in frame) | Sz | Field |
|---|---|---|
| 30 | 1 | `TOTAL=4` |
| 31 | 1 | `IDX 0..3` (`bytes = IDX*98 .. IDX*98+97`) |
| 32 | 4 | `PREV_HASH u32 (FNV1a of last tick world)` |
| 36 | 98 | `CHUNK` |
| 134 | 8 | `TAG` |

`FRAG_N=4, FRAG_BYTES=98`. IDX order irrelevant.

### 2.2 INTENT node->Korvo unicast, 48B

Payload 10B after header:

```
base_tick u32 (=last SNAP tick seen) +
seq u16 per-node monotonic from 0 +
cmd[4] (vx i8, vy i8, mode u8, sensor u8) +
flags u8 (bit0 E-STOP) + res u8=0 + TAG(8)
```

### 2.3 EVENT Korvo->all broadcast, <=78B

Payload: `event_id u16 monotonic, apply_tick u32, e_kind u8 (1=TARGET_APPEAR,2=LINK_DOWN,3=FOUND), len u8, data[0..32] + TAG`. Repeated in every SNAP tick until acked (see §4). Nodes journal `applied/skipped`.

### 2.4 RESYNC_REQ node->Korvo unicast, 46B

Payload 8B: `want_tick u32 + have_hash u32 + TAG`. Sent on boot, gap>cap, or hash mismatch.

### 2.5 RESYNC_REPLY Korvo->node unicast, 142B

Same layout as SNAP_FRAG + `KIND=5`, `TICK=want_tick`. Sends all 4 frags unicast back-to-back + one EVENT replay bundle. Receiver treats as snapshot for that tick.

## 3. Fragmentation / reassembly / drop

* Single-slot reassembly: `buf[4][98] + bitmask + tick`. New `TICK>cur` clears slot. `TICK<cur` dropped. Cross-tick frags never merged.
* **Drop-partial:** if at `TICK+1` arrival mask != `0xF`, drop whole `TICK`, count `gap`, interpolate `T-1..T`. No NACK for SNAP.
* Expiry 250ms. Thresholds: `<300ms Live, <1s Stale (interpolate/freeze last), >1s Resync (send RESYNC_REQ, freeze render, keep journaling)`.
* Dead-reckon cap: max 10 ticks linear extrapolation, then freeze. Never extrapolate events.

## 4. Loss / dup / default

* SNAP: idempotent last-writer-wins keyed by `(CYCLE,TICK)`. Dup `IDX` overwrite, no error.
* INTENT: Korvo keeps `last_seq[node]`. Accept iff `seq>last_seq && base_tick<=T`. Uses newest `seq<=T-2` for tick `T` (2-tick pipeline). **Missing/dup/old = `HOLD + keep sensor`** (vx=vy=0, mode/sensor unchanged). Dups suppressed, no NACK.
* EVENT: reliable via repetition + ack bitmap in INTENT `flags` piggyback or `RESYNC_REPLY`. Node applies once per `event_id` at `apply_tick`, dups skipped.

## 5. Version negotiation (mgmt channel, run start)

1. Korvo mgmt `RunAnnounce{proposed_version=1, run_id, seed, tick_hz=10, frag_n=4}`.
2. Each node mgmt reply `SimHello{supported=[1], sender}`. Host-twin same.
3. Start SIM only if all 16 ack `1` within 5s, else **abort run**.
4. Abort/falsify if: mixed `VERSION`, `TICK` rollback without new `RUN_ID`, `CYCLE` change without new `RUN_ID`, or Korvo-log vs node-log snapshot-hash divergence for same `run_id+tick`.

## 6. Journal (SD, verbatim)

Journal `run_id+VERSION+seed` on RunAnnounce. Per tick append:
`TICK, KIND, SENDER, frag_mask, intent_seq, world_hash(FNV1a-32 of 392B), prev_hash, event_id/applied|skipped|gap|drop_reason`
* Full SNAP hash every tick, not just frag hash. Torn-write protection: 64B header + CRC32 per line, readback-verify on open, stop-sim on full disk (keep mgmt alive).

## 7. Summary

| Kind | Dir | Size | Reliability | Loss rule | Journal |
|---|---|---|---|---|---|
| SNAP_FRAG | Korvo bcast | 142B x4/tick | unreliable, idempotent | drop-partial tick, interpolate, cap 10, freeze | tick, mask, world_hash, gap |
| INTENT | node uni | 48B | unreliable, seq | newest <=T-2 else HOLD+sensor | seq, base_tick, drop-dup |
| EVENT | Korvo bcast | <=78B | reliable-repeat | repeat till ack, apply-once | applied/skipped + id |
| RESYNC_REQ | node uni | 46B | retry 500ms x3 | — | want_tick, have_hash |
| RESYNC_REPLY | Korvo uni | 142B x4 | retry on req | checkpoint replace | catch-up hash chain |
