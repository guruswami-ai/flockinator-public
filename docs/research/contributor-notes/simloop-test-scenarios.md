<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Supervisor-reviewed before use; not yet adopted. -->

# Host Loop Integration Tests — Fault-Focused
**Harness:** 1 controller + 16 panels `R00-R15`, seeded sim only. Loop: `WorldCore (velocity intents) -> Decision -> Fragmented Snapshot Wire -> Per-tick Journal`. Decision: `signal>=0.70 => DOUBLE_CHECK, elif obstacle/missing => WAIT, else SEARCH`.

## S1: Single fragment drop
- **Setup:** Seed 101, tick 50, `R03` moving `vx=1.0`. Snapshot 4 frags.
- **Fault:** Drop `frag 2/4` for `R03`.
- **Expected:** No move: `pos[t]==pos[t-1]`. Decision=`WAIT`. Journal: `tick=50,R03,3/4,MISSING,WAIT`.

## S2: Full tick loss for one robot
- **Setup:** Seed 101, tick 51, all robots `SEARCH`.
- **Fault:** Drop all frags for `R07` (100% packet loss).
- **Expected:** `R07` intent zeroed, `WAIT`. Others advance. Journal marks `R07: 0/4, PACKET_LOSS`.

## S3: Stale snapshot arrives late
- **Setup:** Seed 202, tick 60-63, `R11` at `signal=0.40`.
- **Fault:** Delay tick 60 snapshot to arrive at tick 63.
- **Expected:** Reassembler discards `tick<current`. No rollback. Journal tick 63: `STALE_DISCARD tick=60`. `R11` uses tick 63 or `WAIT` if missing.

## S4: Duplicate fragment retransmit
- **Setup:** Seed 202, tick 64, snapshot 3 frags.
- **Fault:** Send `frag 1/3` x3 for `R02`.
- **Expected:** Dedup by `(tick,frag_idx)`. Applied once. Single `SEARCH` move, no double velocity. Journal: `dup=2 dropped`.

## S5: Out-of-order + interleaved robots
- **Setup:** Seed 303, tick 70, `R00-R03` active.
- **Fault:** Deliver frags reverse order `3,2,1,0` interleaved across robots.
- **Expected:** Correct reassembly after all frags. All 4 move normally. Journal: `reordered=true, decision=SEARCH`.

## S6: Panel node reboot mid-search
- **Setup:** Seed 404, tick 80, `R09` `SEARCH`, `signal=0.65`.
- **Fault:** Reboot `R09` at tick 81, RAM/state cleared.
- **Expected:** `R09` emits `HELLO+RESYNC_REQ`, intent=`0`, `WAIT`. World freezes `R09`. Controller sends full snapshot next tick. Journal: `81: REBOOT, 82: RESYNC_OK`.

## S7: Controller reboot / journal gap
- **Setup:** Seed 404, tick 90 continuous journaling.
- **Fault:** Restart controller, skip ticks 91-92.
- **Expected:** On boot journal shows `GAP 91-92, last_tick=90`. WorldCore halts intents until resync. No phantom moves. Replay from seed 404 reproduces pos up to 90.

## S8: High signal + corrupt fragment
- **Setup:** Seed 505, tick 100, `R14` `signal=0.85`, `obstacle=false`.
- **Fault:** Corrupt 1 frag checksum (bit-flip), rest valid.
- **Expected:** Frag dropped, snapshot incomplete. `WAIT` overrides `DOUBLE_CHECK`. No false find reported. Journal: `R14, CHECKSUM_FAIL, WAIT, find_claim=false`.
