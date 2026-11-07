<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Supervisor-reviewed before use; not yet adopted. -->

## Review: `World` deterministic core — C-port blockers

Total size OK: `8 + 16*24 = 392B`. `<` little-endian explicit is good. Rest is **not** C-safe.

### Critical — Python/C diverge

1. **Floor-div vs trunc: `vx // 10` in `step()`**
   Python floors, C truncates toward zero. `vx=-15`: Python `-2`, C `-15/10 = -1`. Kinematics diverge for any negative `vx,vy % 10 != 0`. Fix: define trunc division + test, promote to `int32` before add/clamp in C.
2. **Float leak: `int((vx*vx+vy*vy)**0.5)`**
   Violates "no floats in state". Python `float.sqrt` + `int()` truncation != C `isqrt` / `sqrtf`. ESP32 float + determinism risk. Fix: `math.isqrt(vx*vx+vy*vy)`.
3. **Negative `%` on heading: `(heading ±5) % 3600`**
   Python `-5 % 3600 == 3595`, C `-5 % 3600 == -5`. Diverges on first southward step. Fix: `(heading+3600+delta)%3600` with unsigned arithmetic.
4. **C `struct` padding vs `REC=<hhHhBBBBhhII`**
   Python `struct` is packed. Naive C `struct` will pad before `II` to 26-28B, breaking 24B/392B wire. Must use `__attribute__((packed))` + `static_assert(sizeof==24)`.

### High — encode/decode asymmetry, overflow

5. **Unbounded ints vs fixed width.** `snapshot()` does no range check. Python raises `struct.error` on overflow, C wraps/truncates. Must clamp/mask explicitly: `x,y,tx,ty,speed:int16`, `heading:uint16`, `mode/flags/ack/rssi:uint8`, `tick:uint32` wrap, `sensor:uint32`. Same for 16-bit add: do math in 32-bit then clamp.
6. **`rssi` as `B` unsigned.** Wire `BBBB` = unsigned. Real RSSI is negative `int8`. Current `0` hides it. Future `-70` packs in Python = exception, in C `uint8_t` = `186`. Change to `b` or offset-encode, decide now.
7. **`HIDDEN=0x7FFF` sentinel collision.** `h` max = `32767`. Robot clamp `±32000` preserves gap, but `survivor` is never clamped/validated. Survivor `(32767,y)` indistinguishable from hidden. `decode()` never maps `(HIDDEN,HIDDEN)->None`. Round-trip broken: `None -> (32767,32767) -> (32767,32767)`.
8. **No length check in `decode()`.** Slices `data[:8]`, `data[8+i*24:...]` silently ignore trailing bytes, raise opaque `struct.error` if short. Need `if len(data)!=392: raise`.

### Medium — logic / units / spec bugs

9. **Unit mismatch.** Doc: `x` in dm @10Hz, `vx` in cm/s. Correct dm-step = `vx/100` per tick. Code does `vx//10` = 10x too large. If `x` is actually cm, doc/init/survivor wrong. Also `MAX_SPEED=300`, `speed=isqrt<=424`, so `speed` clamp `0..32000` is dead code.
10. **Heading ignores `vx`.** `delta = +5 if vy>0 else -5 if vy<0 else 0`. Pure `+x` motion never turns. Not an atan2 approx, just drift. Pre-reg behavior misleading.
11. **`seed` unused.** Stored, never used for init/RNG. "Fixed seeds" give identical worlds; different seeds also identical. Falsification/pre-reg meaningless until RNG is `isqrt`/LCG-based and shared with C.
12. **`intents` unvalidated.** Missing=HOLD ok, but extra keys, `None`, floats silently accepted. `vx(float)//10` -> float, then `REC.pack` fails. C expects `int16[16][2]`. Enforce `int(vx)`, reject `id<0 or >=16`.

### Low — hygiene

* `assert HDR.size/REC.size` stripped under `python -O`. Use explicit `if !=: raise`.
* Reserved `0` (`II` second word) packed but dropped in `decode` (`v[11]` ignored) and never validated `==0`.
* `tick: I` will raise at `2**32` in Python, wrap in C. ~49d at 10Hz? Actually `2**32/10/86400 ≈ 4971d`. Document wrap.
* `mode/flags/ack_seq/tx/ty/sensor` never mutated in `step()` — dead wire fields, OK but must init explicitly in C to `0/1/0`.
