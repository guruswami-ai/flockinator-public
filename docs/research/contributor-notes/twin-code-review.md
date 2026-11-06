<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Supervisor-reviewed before use; not yet adopted. -->

## Verdict: not parity-safe as-is

`decide()` logic and FNV-1a core are correct, but `run_twin()` cannot bit-match a correct C++ port, and `parity()` can report `1.0` on truncated journals.

### Critical: host/device will diverge

1. **Non-portable RNG:** `random.Random(seed)` is Mersenne-Twister + Python `genrand_res53` / `uniform()` float transform. ESP32 C++ `mt19937` / `uniform_real_distribution` / `esp_random()` / Arduino `random()` produce different streams for same `seed`. Seeded parity impossible without explicit integer PRNG in spec (e.g. SplitMix32/xorshift, integer draws only).
2. **Float-quantize rounding mismatch:** `int(round(signal*1000))` uses Python banker's rounding (ties-to-even). C `round()/lround()` is half-away-from-zero. Ex: `122.5 -> 122` in Python, `123` in C. Every `*.5` LSB diverges `input_hash`.
3. **Decide on raw float vs quantized int:** `decide(signal,...)` uses binary64 `signal`, hash uses `signal_q`. Near `T_HI=0.70` (not binary-exact), `signal=0.6996 -> SEARCH` but `signal_q=700 -> 0.70 -> DOUBLE_CHECK` if device does `decide(q/1000.0)`. Spec must define decision on `q >= 700`.

### High: spec / parity bugs

4. **`parity()` ignores length mismatch:** `n=min(len(host),len(device))`. Host 500 rows vs device 400 truncated rows with matching prefix => `{"compared":400,"agree":400,"parity":1.0}`. Must require `host_rows==device_rows==compared`, else fail + `length_mismatch:true`, `parity:0`/`None`.
5. **Thresholds not frozen:** `T_HI,P_OBS,P_LOSS` correct, but `run_twin(..., p_loss, p_obs)` lets caller silently violate canary v1. Remove args or `assert p_loss==P_LOSS and p_obs==P_OBS`.
6. **Float threshold comparisons not portable:** `signal >= 0.70`, `random() < 0.10/0.05` on binary64 vs binary32/libm will differ at boundary. Must compare integers: e.g. `q>=700`, `u32 < UINT32* p`.

### Medium

7. **Coupled world stream:** `rng_world` shared for `signal` (`uniform()`=1 `random()` draw) + `obstacle` (1 draw). Deterministic but fragile; add/remove of one draw cascades other. Use 3 independent streams: signal / obstacle / loss, documented order.
8. **`parity()` undiagnostic:** only joint `decision+hash` agree. Report `hash_mismatch` vs `decision_mismatch` separately, check `tick` sequence, don't `round(agree/n,4)`.
9. **Seed mapping:** `seed ^ 0x5BD1E995` + Python `Random` seeding != C++ `uint32_t` seeding. Negative/large `seed` diverges. Spec must define `uint32_t` seeds and transform.

### Low

10. `import hashlib` unused. `int(round(...))` redundant. `latency_us:0` placeholder breaks naive CSV diff (correct that `parity()` ignores it, document it). Hash format `f"{h:08x}"` lowercase — confirm device uses same, not `%08X` / `0x` prefix. `encode()` defaults to UTF-8 — fine for `0-9:` but pin to `ascii`.
