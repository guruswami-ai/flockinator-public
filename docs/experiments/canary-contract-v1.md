# Canary contract v1.1 (single aligned version)

This contract supersedes the decision-rule, enum, timeout and
journal text in
[panel-policy-canary-preregistration.md](panel-policy-canary-preregistration.md)
wherever they differ. One versioned contract governs the host
twin (`kulira_core/twin.py`), the SIM wire reference
(`kulira_core/simwire.py`), and any future panel firmware port.
Changes require a version bump here, never silent edits.
Changelog: v1.1 adds missing-input/loss semantics (issue #131)
and snapshot-replay rejection (issue #130); v1 was the initial
alignment.

## Decision table (inputs are per-tick, quantized)

Inputs: `signal_q` int 0-1000, `obstacle` bool, `pkt_loss` bool
(packet missing or >500 ms stale counts as `pkt_loss`).

| Priority | Condition | Decision | Enum |
|---|---|---|---|
| 1 | `pkt_loss` | WAIT | 2 |
| 2 | `obstacle` | WAIT | 2 |
| 3 | `signal_q >= 700` | DOUBLE_CHECK | 1 |
| 4 | otherwise | SEARCH | 0 |

Enums are frozen: `0=SEARCH, 1=DOUBLE_CHECK, 2=WAIT`.
Comparisons are integer (`signal_q`), never raw float.

## Journal row (device SD and host twin, identical)

CSV header: `tick,seed,input_hash,decision,latency_us`

- `input_hash`: FNV-1a-32 over `"{tick}:{seed}:{signal_q}:{obstacle}:{loss}"`, 8-char lowercase hex.
  Rendering is frozen: decimal integers, booleans as `0`/`1`
  (`int(bool)`), UTF-8, colon separators, no padding. The golden
  vectors were produced with exactly this rendering; any other
  rendering is a different hash and will mismatch all 300 rows.
- `latency_us`: device-measured; host writes 0. Comparator ignores this column.
- Row identity is `(tick, seed)`: a comparator must verify both
  match positionally; altered tick/seed is a mismatch, not a pass.

## Parity definition

Parity = rows where **both** `input_hash` and `decision` agree,
divided by compared rows. Length mismatch between host and
device journals is a completeness failure: parity is reported
as `None`, never as a truncated-prefix score. Hash mismatches
and decision mismatches are also reported separately.

## Missing-input evidence and loss semantics (v1.1, issue #131)

Defined BEFORE any hardware collection, so loss cannot be
reinterpreted after the fact:

- A tick with no received snapshot (or one stale by >500 ms)
  is a **missing-input tick**. The device still journals exactly
  one row for it: `input_hash = missing_hash(tick, seed)`
  (FNV-1a-32 over `"missing:{tick}:{seed}"`, see
  `kulira_core/twin.missing_hash`), `decision = WAIT (2)`.
  Missing rows are how completeness is proven under loss;
  absent rows are a journal failure, not "loss".
- Parity treats missing-input rows separately: they count in
  `missing_input_rows`, agree iff the decision is WAIT, and are
  never hash mismatches (the device cannot hash input it did
  not receive). Host input generation models loss with the
  seeded net stream; the device is scored on what arrived.
- Loss levels for the canary gates are defined on *delivered*
  ticks: parity is computed over rows present in both journals
  plus missing-input rows; a run where >50% of ticks are
  missing-input is reported as a link failure, not scored as a
  policy result.
- Snapshot replay is not loss recovery: completed or stale
  snapshots are rejected (`simwire.Reassembler.completed_tick`),
  so a replayed tick can never masquerade as a live input.

## Wire alignment

SIM snapshot/intent/event frames follow `kulira_core/simwire.py`
(30B header, context = run_id + seed + cycle; mixed-context
fragments at the same tick are rejected).
