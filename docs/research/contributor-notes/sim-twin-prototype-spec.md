<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Supervisor-reviewed before use; not yet adopted. -->

## Host Simulation Twin — Prototype Spec

Simulated data only. Parity comparator for future ESP32 SD journal test. `stdlib`-only, deterministic.

### 1. Module layout
```
host_twin/
  twin.py      # decide(), tick_inputs(), run(), input_hash()
  cli.py       # argparse: --seed --ticks --out
  test_twin.py # 6 unit tests below
```
Allowed imports only: `random, struct, argparse, csv`. No `time, datetime, os.urandom, numpy`.

### 2. Exact decision rule — v1, stateless, pure
Thresholds fixed: `T_HI = 0.70`, `P_OBS = 0.10`, `P_LOSS = 0.05`

```python
def decide(signal: float, obstacle: bool, pkt_loss: bool) -> int:
    # 0=SEARCH, 1=DOUBLE_CHECK, 2=WAIT
    if pkt_loss:
        return 2
    if obstacle:
        return 2
    if signal >= 0.70:
        return 1
    return 0
```
Priority order is normative: `LOSS > OBSTACLE > SIGNAL`. No hysteresis, no cross-tick state.

Tick input generation, fixed consumption order per tick:
```python
rng_world = random.Random(seed)
rng_net   = random.Random(seed ^ 0x5BD1E995)
for tick in range(N):
    signal   = rng_world.uniform(0.0, 1.0)
    obstacle = rng_world.random() < 0.10
    pkt_loss = rng_net.random() < 0.05
    decision = decide(signal, obstacle, pkt_loss)
```

### 3. Determinism requirements
1. **No wall clock:** no `time.*`, no latency measurement on host.
2. **Separate RNG streams:** `world` vs `net`. Never use global `random.*`. Init once per run from `seed`.
3. **Canonical quantization:** `signal_q = int(round(signal*1000))` for hashing/logging. No raw float compare except `decide()`.
4. **Pure functions:** `decide(), input_hash()` have no I/O, no globals.
5. **Fixed order:** consume `signal, obstacle, loss` in that order every tick.

### 4. Log schema — identical to ESP32 SD journal
CSV, `,\n`, header mandatory:
```
tick,seed,input_hash,decision,latency_us
```
| field | format |
|---|---|
| `tick` | `int`, 0-indexed |
| `seed` | `int`, run seed |
| `input_hash` | 8-char lower hex, FNV-1a32 over `f"{tick}:{seed}:{signal_q}:{obstacle:int}:{loss:int}"` |
| `decision` | `0,1,2` |
| `latency_us` | host: always `0` placeholder; device: measured micros; comparator **ignores** this column |

Example:
```
tick,seed,input_hash,decision,latency_us
0,42,a3f1c902,0,0
1,42,7b22e110,2,0
2,42,c91d04aa,1,0
```
FNV-1a32 reference (mirror on ESP32 in C++):
```python
def input_hash(tick, seed, sq, ob, lo) -> str:
    h = 0x811c9dc5
    for b in f"{tick}:{seed}:{sq}:{ob}:{lo}".encode():
        h ^= b; h = (h * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"
```

Parity check: `diff <(cut -d, -f1-4 host.csv) <(cut -d, -f1-4 device.csv)`

### 5. 6 unit tests to write
1. `test_determinism`: `run(seed=42,N=1000)` twice → byte-identical CSV.
2. `test_seed_sensitivity`: `seed=42` vs `43` → different hashes, same header.
3. `test_rule_truth_table`: loss=1→WAIT; obs=1→WAIT; sig=0.699→SEARCH; sig=0.70→DOUBLE_CHECK; loss+high-sig→WAIT.
4. `test_no_banned_imports`: AST scan `twin.py` rejects `time,datetime,os,sys.random,numpy`.
5. `test_schema_parity`: header exact, `input_hash` regex `[0-9a-f]{8}`, `decision in {0,1,2}`, `latency_us==0` for all host rows.
6. `test_stream_isolation`: vary `P_LOSS` only → `signal` sequence unchanged; vary `P_OBS` only → loss sequence unchanged.
