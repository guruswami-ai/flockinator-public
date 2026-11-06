<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Supervisor-reviewed before use; not yet adopted. -->

## Review: `sim-wire-format-v1` reference vs. code

All snapshot frames as built are legal: `30 + (6+98) + 8 = 142B <= 160B`. No fixed `snapshot_frames()` output exceeds MTU. Exceedance is only possible via generic `pack_frame()` misuse, and the guard is broken.

### High

* **Reassembler: `idx`/`total` unchecked — slot poison/DoS.** `feed()` never checks `total==4` or `idx<4`. `idx=4..255` sets `mask |= 1<<idx`, so `mask` can never `==0xF` again (e.g. `0x1F`). Valid 0-3 fragments for that `tick` then never complete. Also mixes forks.
  *Fix: `if total!=4 or idx>=4: return None`.*
* **Reassembler: short/overlong payload accepted.** `payload[6:6+98]` with no length check. Short chunk -> poisoned `parts[idx]`; completes later with `len(world)!=392 -> None` but slot stays poisoned. Long payload `>104B` (up to 122B allowed by `pack_frame`) silently truncated. *Fix: `if len(payload)!=6+98: return None`.*
* **Reassembler: crash on `len(payload)<6`.** `struct.unpack("<BBI", payload[:6])` raises `struct.error`, contrary to `unpack_frame` "return None on any validation failure" philosophy. Remote DoS. *Fix: length guard before unpack.*
* **Reassembler: duplicate-after-complete re-emits.** `mask`/`parts` not cleared after `mask==0xF`. Duplicate frag for same `tick` returns `world` again. Violates apply-once expectation. *Fix: reset to `None/0` or latch `done` tick.*
* **Reassembler: same-tick fork merged, hash-chain dead.** `prev_hash` latched only on tick change; later frag with different `prev_hash` same `tick` merged. `prev_hash` never verified, `fnv1a()` defined but never called. *Fix: reject `prev_hash` mismatch within tick, verify against `fnv1a(prev_world)`.*
* **IntentGate: newest-overwrites + sticky replay.** `offer()` overwrites `pending[node]`; `for_tick()` never consumes. Sequence: `seq10/base100` then `seq11/base200` early -> `seq10` lost, spurious `HOLD` at `102`. Conversely old `base_tick << T-2` satisfies `<=tick-2` forever -> same `cmd` executes every tick. No single-use, no expiry window. Breaks "2-tick pipeline" claim. *Fix: queue per-tick intents / consume on use, expire stale.*
* **`pack_frame` MTU enforced only by `assert`.** `assert len(payload)<=122` and `assert len(run_id)==16` vanish under `python -O`. Then can emit `>160B` and wrong-size `run_id` with valid HMAC. *Fix: `raise ValueError`.*
* **`unpack_frame` accepts management/other kinds.** No `kind in (1..5)` or `sender in (0,0xFE)` check, despite module docstring "never accepted for management frames". Accepts `kind=0,6..255`, any sender. *Fix: whitelist.*

### Medium

* **Stale-tick compare breaks on `u32` wrap.** `tick<I`: `tick` is `<I`. After `0xFFFFFFFF->0`, valid wrap looks stale and is dropped forever. Need windowed/modular compare.
* **`RESYNC_REPLY` conflated with `SNAP_FRAG`.** Same slot, same `6+98B` parse. No separate format/run partition; `RESYNC_REQ` silently dropped. A resync for old/new run can corrupt in-progress tick. *Fix: separate slot, check `run_id/seed/cycle`, don't merge kinds.*
* **No run isolation in `Reassembler`/`IntentGate`/`EventTracker`.** Tick-only keying. Different `run_id/seed` fragments merge; `event_id` reuse across runs is suppressed as "duplicate".
* **`EventTracker` unbounded + no late window.** `applied:set` grows forever; `tick >> apply_tick` still applies. Can't distinguish `duplicate` vs `not-yet-due` (both `False`). *Fix: per-run LRU + `apply_tick <= tick <= apply_tick+W`.*
* **Intent `cmd` / `HOLD` unsized.** `offer` accepts any `cmd` length; `for_tick` returns `b"\x00\x00"`. Downstream fixed-point parser has no length guarantee.

### Low

* Hardcoded `30` / `-TAG_LEN` slicing in `unpack_frame` instead of `HDR.size`; `total` field parsed but unused; `gaps` counts 1 per tick-jump not per missed tick; `cycle:H` wraps at 65536; 8B truncated HMAC (`2^32` birthday) — OK for sim-only, must not be reused for management; empty/short `key` not rejected in `_tag`.
