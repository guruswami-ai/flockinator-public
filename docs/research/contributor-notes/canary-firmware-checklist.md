<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Supervisor-reviewed before use; not yet adopted. -->

# ESP32 Panel Canary — Firmware Checklist (Contract v1.1)

**Freeze:** This checklist implements **Canary contract v1.1 only**. Governs `twin.py` + `simwire.py` + firmware. Any change = version bump, no silent edits. Enums frozen: `0=SEARCH, 1=DOUBLE_CHECK, 2=WAIT`. Integer compare only, never raw float.

## 1. Modules (build in this order)

1. `canary_config.h` — `SIG_Q_THRESH=700`, `STALE_MS=500`, enums, `CONTRACT="v1.1"`, `seed`, `run_id`
2. `fnv1a32.cpp` — offset `2166136261`, prime `16777619`, output 8-char lowercase hex, zero-padded
3. `policy.cpp` — pure function, no I/O:
```
if pkt_loss -> WAIT(2)          // missing OR stale>500ms, priority 1
else if obstacle -> WAIT(2)     // priority 2
else if signal_q>=700 -> DOUBLE_CHECK(1) // priority 3, int compare
else SEARCH(0)
```
4. `journal.cpp` — SD CSV append, header exactly: `tick,seed,input_hash,decision,latency_us`
5. `tick_input.cpp` — quantize + `pkt_loss` detector via `millis()`: `now-last_rx_ms>500 => pkt_loss=true`
6. `simwire_port.cpp` — 30B header, context=`run_id+seed+cycle`; reject mixed-context fragments at same tick; reject replay via `completed_tick` (replay != recovery)
7. `main.cpp` — tick loop: measure `t0=micros()`, decide, hash, journal, `latency_us=micros()-t0`

## 2. Order + On-device test per stage

- [ ] **S1 Hash:** port FNV-1a. Test: 3 vectors from `twin.missing_hash` + `twin.hash`. Must match hex exactly. Formatting is `"{tick}:{seed}:{signal_q}:{obstacle}:{loss}"` and `"missing:{tick}:{seed}"` — copy `twin.py` verbatim (bool encoding 0/1 vs True/False). Any mismatch = stop.
- [ ] **S2 Policy:** unit-test decision table: loss=1->2, obstacle=1->2, q=700->1, q=699->0, q=1000->1, loss+obstacle+q=1000->2. Serial `PASS/FAIL`.
- [ ] **S3 Journal:** write 5 rows to SD, power-cycle, verify header + `tick,seed` positional identity on host. `latency_us` device-measured (host writes 0, comparator ignores it, but column must exist).
- [ ] **S4 Loss semantics:** inject no-packet and 501ms-stale ticks. Must still journal 1 row/tick: `input_hash=missing_hash(tick,seed)`, `decision=2`. Absent row = journal failure, not "loss".
- [ ] **S5 Simwire:** feed mixed-context fragments + replayed `completed_tick`. Must reject both. Live tick only.
- [ ] **S6 Golden gate:** replay **300 golden input rows** offline (SD file, no radio). Require **300/300 exact** `input_hash` + `decision` match vs host twin. **No radio work until this passes.**

## 3. Budgets to record (per panel, in `budget.json`)

| Metric | Budget | Record |
|---|---|---|
| Decision compute (no SD) | <5ms, target <500µs | `latency_us` p50/p99/max |
| SD row append + flush | <20ms | max observed |
| Tick deadline | <100ms (stale threshold 500ms must never be caused by self) | worst tick |
| RAM / Flash | report `idf.py size` + free heap at boot/tick 300 | numbers |
| SD size | ~35B/row, 300 rows ~10.5KB | bytes |

Log `tick,seed,latency_us` histogram; flag any `latency_us>5000`.

## 4. Failure handling

* **SD write fail:** retry 3x with flush+reopen. On persistent fail: freeze in `WAIT(2)`, blink status LED, keep last 32 rows in RTC RAM, do NOT skip ticks or fabricate hashes. Hand back partial file as-is (will score `parity=None` completeness failure).
* **Reboot mid-run:** on boot check for open journal. Never append/resume. Close old file as-is, create new `journal_{run_id}_{seed}_b{N}.csv`, log `boot.log` with `reboot_tick, millis()`. Incomplete file = completeness failure by design.
* **>50% ticks missing-input:** continue journaling WAIT rows, but flag `LINK_FAILURE` in report — not scored as policy result.

## 5. Evidence handoff for scoring

Per panel, return verbatim (no edits):
1. `journal_{run_id}_{seed}.csv` — full run, one row/tick incl. missing rows
2. `golden_verify.log` — 300/300 proof, with `CONTRACT=v1.1`, `twin.py` commit, seed
3. `budget.json` — table from §3
4. `config.json` — `contract, run_id, seed, thresh=700, stale_ms=500, firmware_sha`
5. `boot.log` — boots/reboots during run

Scoring: `parity = rows(both hash+decision agree)/compared rows`. Length mismatch host vs device = `None` (never truncated-prefix). Missing rows agree iff decision=WAIT, never count as hash mismatch.
