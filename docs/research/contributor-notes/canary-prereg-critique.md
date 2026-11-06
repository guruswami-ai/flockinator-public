<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Supervisor-reviewed before use; not yet adopted. -->

## Pre-reg critique: panel-policy canary

**All simulated. No SAR, radio, or fleet claim.**

### 1. Seed allocation conflict

* **Reuse across gates:** Gate 0 smoke uses `seed 40, 50 ticks`, then Gate 1 reuses `40-59 x 500 ticks` into same `/sd/journal/search_test.csv`. That guarantees duplicate `tick` for seed 40 or forces manual wipe — which violates H3 `exactly one row per tick`.
* **Reuse across loss levels:** Same 20 seeds at 0%/5%/10%/20% is paired by design, but not declared as paired. Without pre-committed drop masks, you can't distinguish world-randomness from drop-randomness.
* **No registry check:** `40-59` is not shown as reserved vs `docs/research/contributor-notes/` drafts. High collision risk if other canaries use 0-99.

> Fix: reserve one range centrally. Use e.g. seed `39` for smoke only, `40-59` locked for this test, separate file per run.

### 2. Gates not measurable from DUT SD alone

Scored evidence is defined as *only* DUT SD with `tick,seed,rx_hash,signal,conf,decision,latency_ms,free_heap,dropped_flag`. These cannot be proven from that:

* **Gate 0 `other 15 displays unaffected`:** no data source. Not in schema, host logs explicitly excluded.
* **`p95 latency <200ms`:** self-reported `latency_ms` (RX-interrupt -> flush). No external RX timestamp to check against. Panel can under-report delay or ISR deferral.
* **`min heap >20kB`:** sampled once per tick at log time. Misses between-tick dips, ISR stack, and by definition misses the heap value that caused a crash.
* **`zero crash/reboot`:** absence of rows looks identical to controller stop, power loss, SD stall. No `boot_id, reset_reason, uptime`.
* **`dropped rate == injected ±1%`:** contradiction. Loss truth is `hash(seed,tick)` on controller, but `No host logs count`. DUT only sees gaps, cannot prove injector did 5/10/20%.
* **`100% of >500ms timeouts -> WAIT`:** tick is clock @5Hz (200ms). `>500ms` = >2 ticks missing. Offline `twin.py` replaying SD rows cannot reconstruct wall-time to verify the 500ms branch was taken correctly, only that `dropped_flag=1`.
* **`rx_hash` audit:** DUT-computed hash with no stored raw payload or controller truth hash. Corrupted payload that still parses will match twin replay tautologically.

Parity here is **replay-parity**, not correctness. Twin replays logged `signal,conf`, not independent world model.

### 3. Missing failure cases

* **DUT reboot mid-run:** No `BOOT` marker row, no NVS `boot_seq`. After reboot `tick` jumps, heap resets, duplicates possible. Current H3 auto-fails, Exclusions allows dropping the run as `power loss` — survivorship bias.
* **Controller restart:** `tick` regresses to 0, seed may restart. DUT will log duplicate ticks, violating H3. No tick-monotonicity check, no epoch ID, no void rule.
* **SD full / flush fail / corrupt row:** Flush-per-tick at 5Hz blocks latency budget. No pre-run free-space check, no flush-error code, no handling of torn write.
* **MGMT `STOP` lost:** DUT has no auto-stop after 500 ticks. If `STOP` is missed it appends tick 501+, violating `exactly one row`.
* **Bad SIM payload:** Rule covers only timeout + `conf` thresholds. No rule for bad `rx_hash`, NaN `conf/signal`, out-of-range `obstacle/pose`. Twin behavior undefined.

### 4. Overclaim from n=1

> *can 1 low-cost panel replicate twin logic live + journal it while 15 peers run normally.*

* One bench unit `PANEL-00` ≠ fleet. No inter-device variation, temp/voltage, flash wear, antenna orientation.
* 15 peers `stay powered, ignore broadcast` ≠ 16-node scaling, contention, or coexistence. Peers-idle proves nothing about 16 deciders.
* Zero reboots in ~40k ticks (~2.2hr @5Hz) on one unit ≠ reliability.
* Must scope claim to: this firmware `sha256` on this unit replaying logged inputs.

### 5. Edits required before lock

1. **Seed + file isolation:** Smoke = seed 39 only, Gates 1/2 = 40-59. One file per gate/seed: `/sd/journal/g1_seedNN.csv`. Pre-commit drop masks + `sha256`. Confirm no overlap with contributor-notes registry.
2. **Fix schema:** add `boot_id,reset_reason,raw_hash_expected` + `BOOT` row on setup(). Persist `boot_id` in NVS.
3. **Define reboot/restart as void, not silent exclude:** any `boot_id` increment or `tick` regression voids run. Report intention-to-treat table: runs started / voided / analyzed.
4. **Allow one controller truth artifact:** precomputed `drops_seedNN_lossPP.csv` committed before START, usable only to score drop-rate. Otherwise keep `no host logs` rule.
5. **Make unmeasurables measurable or drop:** peer-unaffected needs observer checklist/photo; latency needs logic-analyzer spot-check or downgrade `latency_ms` to diagnostic only; heap/crash needs `boot_id` + gap analysis.
6. **Add auto-stop:** DUT stops logging after 500 ticks post-`START` without `STOP`. Define truncation/dedup rule for H3.
7. **Specify invalid-input behavior:** on `rx_hash` fail / NaN / out-of-range -> `WAIT + dropped_flag=2`, twin must implement same.
8. **Narrow success claim:** `PANEL-00` unit + frozen `sha256`s, replay-parity only. No fleet, reliability, or SAR-effectiveness language.
