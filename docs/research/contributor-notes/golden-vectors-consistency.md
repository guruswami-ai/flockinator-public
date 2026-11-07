<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Supervisor-reviewed before use; not yet adopted. -->

## Check: consistent, if `pkt_loss=0`

Zero-loss file => Priority 1 never fires. Rule reduces to:
`obstacle ? WAIT(2) : signal_q>=700 ? DOUBLE_CHECK(1) : SEARCH(0)`

* `tick 0: 271, obstacle 0` -> **SEARCH (0)** - P4 otherwise
* `tick 1: 542, obstacle 1` -> **WAIT (2)** - P2 obstacle, signal irrelevant
* `tick 2: 708, obstacle 0` -> **DOUBLE_CHECK (1)** - P3 `>=700`

### Firmware blockers

1. **Hash string not frozen:** contract `"{tick}:{seed}:{signal_q}:{obstacle}:{loss}"` doesn't specify `obstacle/loss` rendering. `0/1` vs `True/False` vs `true/false` => different FNV-1a-32. Must freeze to e.g. `f"{tick}:{seed}:{signal_q}:{int(obstacle)}:{int(pkt_loss)}"` utf-8, plus `pkt_loss` vs `loss` name.
2. **Header mismatch:** golden `tick,seed,signal_q,obstacle,pkt_loss,input_hash,decision` ≠ contract journal `tick,seed,input_hash,decision,latency_us`. Use golden as stimulus+expected only; device must emit 5-col journal.
3. **Stale rule offline:** `>500ms stale => pkt_loss` can't be evaluated in replay. Take `pkt_loss` column verbatim, don't recompute.
