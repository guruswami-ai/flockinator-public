<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Supervisor-reviewed before use; not yet adopted. -->

## 1. Expected action distribution

Rule per tick, in order:
`missing -> wait`, else `obstacle=1 -> wait`, else `signal>=0.70 -> double-check`, else `search`.

Assume independent: `P(obstacle)=0.10`, `P(signal>=0.70)=0.30`, `P(missing)=m`.

Arithmetic:

- `P(wait) = m + (1-m)*0.10 = 0.10 + 0.90*m`
- `P(double-check) = (1-m)*0.90*0.30 = (1-m)*0.27`
- `P(search) = (1-m)*0.90*0.70 = (1-m)*0.63`

| m | wait | double-check | search |
|---|---|---|---|
| **0** | `0.10` = **10%** | `1*0.27` = **27%** | `1*0.63` = **63%** |
| **0.05** | `0.10+0.045`=**14.5%** | `0.95*0.27`=**25.65%** | `0.95*0.63`=**59.85%** |
| **0.10** | `0.10+0.09`=**19.0%** | `0.90*0.27`=**24.3%** | `0.90*0.63`=**56.7%** |
| **0.20** | `0.10+0.18`=**28.0%** | `0.80*0.27`=**21.6%** | `0.80*0.63`=**50.4%** |

Increasing `m` only inflates `wait`, proportionally deflating the other two.

## 2. Fair agreement with missing device rows

Join on `tick_id`, **not row position**. A skipped log shifts all subsequent positional rows.

Let `J` = ticks logged in both, with identical inputs. Let `A` = ticks in `J` with identical actions.

**Recommended primary: pairwise-complete conditional agreement**

> `Agreement = A / J`

i.e. `P(action_device == action_desktop | both logged AND inputs equal)`.

Report separately:
- `Coverage = N_device / N_desktop`
- Input fidelity on `J`
- Lower-bound sensitivity: `A / N_desktop` (treats missing as disagreement)

Why fair: logging drops are missing data, not wrong decisions. Dividing by all desktop ticks penalizes a perfect controller by its drop rate and confounds logging reliability with logic correctness.

## 3. Three disagreement patterns

1. **search <-> double-check flips, wait intact, concentrated near signal ~0.70**
   Most likely: threshold/scaling bug: `>` vs `>=`, 0-100 vs 0-1, float rounding. Not a logic-order error.

2. **One-sided wait mismatch: desktop=wait, device=search/double-check or vice versa**
   Most likely: flag-handling divergence. If correlated with `missing=1`: device reuses last action instead of forced-wait. If correlated with `obstacle=1`: inverted polarity, pull-up, or sampling-time sensor read error.

3. **Bursty / sustained mismatch starting after a gap, disagreement rate ≈ drop rate**
   Most likely: alignment artifact, not control error. Positional join after a skipped row causes off-by-one comparison. Disappears after `tick_id` join.
