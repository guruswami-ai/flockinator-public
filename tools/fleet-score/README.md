# Fleet scorer

Deterministic scoring of planner journals and synthetic host replay. Runtime
scoring uses Python's standard library; pytest is a development dependency.
Run from the repository root:

```sh
uv sync --locked --project tools/fleet-score --group dev
uv run --locked --project tools/fleet-score python -m pytest tools/fleet-score -q
uv run --locked --project tools/fleet-score python tools/fleet-score/score.py validation/kulira/e2e-001
```

`score.py RUN_DIRECTORY` expects `director.json` and unit JSONL journals. Add
`--markdown` for a readable table; otherwise output is JSON. Only synthetic or
sanitized artifacts belong in the public repository. A score is not evidence
that the journal came from a physical node.

## Other entry points

| Script | Purpose | Required arguments |
|---|---|---|
| `baseline.py` | Generate and score host planner replays | `--seeds`, `--out`, `--label` |
| `compare.py` | Compare baseline and candidate aggregate files | `--baseline`, `--candidate`, `--set dev` or `--set holdout` |
| `gate_runner.py` | Apply a named gate config to existing runs | `--baseline`, `--runs`, `--config`, `--out` |

Use `uv run --locked --project tools/fleet-score python tools/fleet-score/SCRIPT.py --help`
for those three parsers. `baseline.py` imports `tools/mission-host`; keep the
sibling tree. Choose a new output directory for each run. Existing registered
seed allocations and archived gates must not be silently changed to improve a
result; new research runs need their declared protocol.

For the repository's frozen reproduction path and artifact interpretation, see
[results](../../docs/results/README.md), [cycle-07](../../docs/results/cycle-07/README.md)
and [build instructions](../../docs/build.md). Historical treatment-vacuity
annotations remain part of those results. Passing tests or a gate alone does not
establish that a treatment was exercised.
