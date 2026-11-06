<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Supervisor-reviewed before use; not yet adopted. -->

## Gate fixes — critique (scorer frozen)

### 1. Baseline dedup + int seed + order-independent join
**Correct direction.**
* **Breaks archives:** any historic `PASS` that relied on positional pairing will flip to `FAIL`/`ERROR` after join-on-`seed_id`. That's intended, but you must re-version gates (`gate-v2`) and re-score — don't overwrite `v1` verdicts.
* **Missing:**
  * Set-equality, not just no-dups: reject on missing/extra seeds. Order-independent is useless without it.
  * Type coercion rule: CSV `1`, `1.0`, `"1"`, `"001"` — define canonical int parsing. Strict `isinstance(int)` will ERROR on legitimate `1.0` exports.
  * Contradictory rows (same `seed_id`, different metrics) vs. exact dup rows — both must ERROR, log differently.
* **ERROR vs FAIL:** `ERROR` correct here — bad reference, can't evaluate.

### 2. Compare unrounded, round only for display
**Correct direction.**
* **Breaks archives:** boundary `PASS`es flip. e.g. threshold `0.05`, true `0.054` displayed as `0.05` -> old `PASS`, new `FAIL`.
* **Missing:** need FP epsilon (e.g. `rate > threshold + 1e-12`) and store `numerator/denominator`. Rate-only hides `1/20` vs `100/2000`. Display must state rounding mode (`round-half-even` vs `half-away`).
* **Verdict:** stays `PASS/FAIL`, no change.

### 3. `UNMEASURED` if treatment never engaged
**Correct to kill vacuous `PASS`, but incomplete.**
* **Breaks archives:** old `PASS` with `n_forged==0` or `n_commits==0` becomes `UNMEASURED`. Dashboards that count `PASS/(PASS+FAIL)` will break — must treat `UNMEASURED` as non-PASS and block rollup.
* **Missing:**
  * Zero vs. insufficient: `1` forged attempt must not yield a measured `PASS`. Need `min_n` / power gate.
  * Define engagement source: controller log vs. 16x panel logs. Who is trusted? Empty log vs. missing log must be distinguished.
  * If protocol *requires* engagement, persistent zero is a harness/liveness `FAIL`, not silent `UNMEASURED`.

### 4. Evidence validation -> currently `ERROR`, should be `FAIL`
**Do not ship as `ERROR`.** All four are system-invariant violations, not harness-unparseable:

* exact-dup discovery, landed-with-no-route, route-with-no-`reserve`, non-finite energy => `FAIL` (penalize SUT). `ERROR` lets a bad run retry until clean and hides gaming.

**Breaks legitimate archives if naive:**
* **Dup discovery:** UDP retransmit from ESP32 panels + quantized ticks can legitimately produce identical `(tick, unit, target)`. Key must be idempotency-id, not full-row hash. Otherwise you ERROR valid history.
* **Landed with no route:** disallow except `t==0` initial placement / explicit spawn state. Specify.
* **Missing `reserve`:** pre-field firmware archives will all `ERROR`. Need `schema_version` check + backfill rule or grandfather `v1` files.
* **Non-finite energy:** JSON can't carry `NaN/Inf` anyway — this only fires on CSV/parquet path or ESP32 float overflow. Also need `energy <0` and `energy > capacity` checks, which you don't have.

**Missing entirely:**
* time monotonicity / clock-skew across 16+1 nodes, teleport / speed-limit, discovery-requires-proximity, route referential integrity both directions, energy conservation (monotonic decrease except recharge events).
