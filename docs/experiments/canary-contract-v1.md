# Canary contract v1 (single aligned version)

This contract supersedes the decision-rule, enum, timeout and
journal text in
[panel-policy-canary-preregistration.md](panel-policy-canary-preregistration.md)
wherever they differ. One versioned contract governs the host
twin (`kulira_core/twin.py`), the SIM wire reference
(`kulira_core/simwire.py`), and any future panel firmware port.
Changes require a version bump here, never silent edits.

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
- `latency_us`: device-measured; host writes 0. Comparator ignores this column.
- Row identity is `(tick, seed)`: a comparator must verify both
  match positionally; altered tick/seed is a mismatch, not a pass.

## Parity definition

Parity = rows where **both** `input_hash` and `decision` agree,
divided by compared rows. Length mismatch between host and
device journals is a completeness failure: parity is reported
as `None`, never as a truncated-prefix score. Hash mismatches
and decision mismatches are also reported separately.

## Wire alignment

SIM snapshot/intent/event frames follow `kulira_core/simwire.py`
(30B header, context = run_id + seed + cycle; mixed-context
fragments at the same tick are rejected).
