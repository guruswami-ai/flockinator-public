# Kulira Core

Seeded, bounded, hash-logged chaos orchestrator. See [docs/kulira-friction.md](../../docs/kulira-friction.md) for the
interference node, friction plan, and adversary model.

## Commands (repo root, on Kulira)

The workspace is an SMB mount; keep the venv off it:

```sh
export UV_PROJECT_ENVIRONMENT="$HOME/.cache/flockinator-kulira-core/venv"
uv sync --project tools/kulira-core
$UV_PROJECT_ENVIRONMENT/bin/python -m kulira_core.cli campaign validate tools/kulira-core/scenarios/false-beacon.json
$UV_PROJECT_ENVIRONMENT/bin/python -m kulira_core.cli campaign run tools/kulira-core/scenarios/false-beacon.json --dry-run --out validation/kulira/false-beacon-001-271828
$UV_PROJECT_ENVIRONMENT/bin/python -m kulira_core.cli campaign report --run validation/kulira/false-beacon-001-271828
$UV_PROJECT_ENVIRONMENT/bin/python -m pytest tools/kulira-core -q
```

Scenarios are JSON. Modules: `disrupt` (drop/delay/duplicate),
`spoof` (forgery/replay + validator), `deceive` (authentic-but-false),
`observe` (scoring), `bridge` (scorer vocabulary), `e2e` (scored lab
run), `rf_inventory` (passive only). Test suite: 65 tests.

## Wall observer commands

```sh
$UV_PROJECT_ENVIRONMENT/bin/python -m kulira_core.cli wall capture --mission <id> --phase beginning --burst 3 --out <session-dir> --adb /opt/homebrew/bin/adb --serial <serial>
$UV_PROJECT_ENVIRONMENT/bin/python -m kulira_core.cli wall verify --session <session-dir>
uv run --with pillow --project tools/kulira-core python -m kulira_core.cli wall report --session <session-dir> --out <report-dir>
```

Timestamped panel stills/video tied to mission phases, with a
hash-chained manifest. See [docs/experiments/wall-observer.md](../../docs/experiments/wall-observer.md).
Dry-run evidence: `validation/kulira/` (disrupt, Glimmer, e2e runs). Live/RF runs require `authorised: true` after review;
network jamming devices are never used — interference is L1/2/3 protocol
technique on the lab network only. Dry-run emits no fleet traffic.
