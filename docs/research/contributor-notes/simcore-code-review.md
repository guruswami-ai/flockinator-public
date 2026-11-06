<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Supervisor-reviewed before use; not yet adopted. -->

## Review: `World` core — not integer-only, not portable

**Verdict: fails host==firmware determinism.** 3 port-divergent behaviours + wrong kinematics.

### Severity list

**[CRITICAL] Float leakage in state: `speed`**
```python
r["speed"] = int((vx*vx+vy*vy)**0.5)
```
Violates "no floats" docstring. `**0.5` is binary-float `sqrt`, `int()` truncates toward zero. C `sqrtf/sqrt/isqrt` will round differently at boundaries. Fix: `math.isqrt(vx*vx+vy*vy)`.

**[CRITICAL] Python `//` != C `/` : position will diverge for `vx,vy<0`**
```python
r["x"] + vx // 10
```
Python floors (`-5//10 == -1`), C truncates toward zero (`-5/10 == 0`). Every negative intent not divisible by 10 diverges by 1 unit/tick. Same for any future `int / int`. Fix: define truncation explicitly + test vector with `-1,-5,-9,-15`, or use fixed-point accumulator.

**[CRITICAL] `heading` is not a heading**
```python
r["heading"] = (r["heading"] + (5 if vy>0 else -5 if vy<0 else 0)) % 3600
```
Ignores `vx` entirely. `vx-only` motion never turns; `vy==0` freezes; otherwise drifts `±0.5°/tick` forever. Not atan2, not quadrant approx. At 10Hz full circle in 72s independent of velocity. C port with real `atan2` LUT will never match. Fix: integer `atan2` LUT or explicit compass-state machine, set absolute not incremental.

**[HIGH] Unit/scale bug 10x**
Claim: `x,y` in dm, `vx,vy` in cm/s, 10 tick/s. `dt=0.1s` -> `dx[cm]=vx/10` -> `dx[dm]=vx/100`. Code adds `vx//10` to dm. 10x too fast. Fix: change state to cm, or `//100` + remainder accumulator.

**[HIGH] Deadzone / remainder loss, no accumulator**
`|vx|<10` -> `vx//10==0`: robot stalls but `speed!=0` and `heading` still advances. Systematic under-integration. Fix: keep `rem_x,rem_y` fixed-point accumulator.

**[HIGH] C-port snapshot fragility, `tick` wrap**
* `tick` Python unbounded, packed `<I`. Python `struct.pack` raises at `2**32`, C `uint32_t` wraps. Must `self.tick = (self.tick+1) & 0xFFFFFFFF`.
* Naive C `struct` will pad `REC` (`BBBB+hh` etc). Must `packed` + `static_assert(sizeof==24)` / total `392B (8+16*24)`. Endianness ok (`<` explicit).

**[MED] Decode/encode asymmetry**
* No `len(data)==392` check. Short buffer: `struct.error`; long buffer: silently ignored trailing bytes.
* `snapshot` packs `sensor,I + reserved I=0` (12 fields), `decode` drops `v[11]` without validating `==0`.
* `survivor=None` -> packs `HIDDEN`, but `decode` returns `(32767,32767)`, never `None`. Round-trip `None != HIDDEN`.
* `HIDDEN=0x7FFF=32767` is max `int16`. Legal survivor at edge collides with hidden sentinel. Reserve out-of-clamp value (clamp world to `±32000` already does this for robots, not for survivor).
* `heading H/u16` vs `speed h/i16`: decode does no range check (`0..3599`, `0..32000`). Out-of-range Python writes raise, C wraps.

**[MED] Input/clamp bugs**
* `_clamp` preserves type: float `vx` -> `vx//10` float -> `r["x"]` becomes float, then packed as `h`. No `int()` coercion/validation of `intents`. Extra/negative node-ids ignored silently.
* `x,y` clamp `±32000` fits `int16 ±32767` only by luck; `speed` clamp `32000` near limit. Any future change overflows `h`.

**[LOW] Dead state / false reproducibility**
* `seed` stored, never used. No RNG. Pre-registration with "fixed seeds" is vacuous.
* `mode,flags,ack_seq,rssi,tx,ty,sensor` never touched by `step()` but snapshotted. Firmware adding logic will diverge with no test hook.
