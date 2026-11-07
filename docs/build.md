# Build and tools

## Firmware

| Target | Build | Notes |
|---|---|---|
| Node | `pio run --project-dir firmware/node-platform -e waveshare-s3` | ESP-IDF; run PlatformIO jobs sequentially |
| Handheld (legacy/recovery-only) | `pio run --project-dir firmware/management-console -e lilygo-s3` | Retired LilyGo T5 prototype; ESP-NOW recovery use only, not an active target |
| Korvo | ESP-IDF 6.1; see `firmware/korvo-monitor/README.md` | Needs pinned ESP-IDF + board SDK; build in a local copy on network-mounted workspaces |

Native tests: `pio test --project-dir <target> -e native` for the node
target (the handheld target is legacy/recovery-only); Korvo portable
model checks are listed in its README.

## Host tools (`tools/`)

| Tool | Purpose |
|---|---|
| [node-commissioner](../tools/node-commissioner/README.md) | USB provisioning, identity/inventory binding, OTA, SD maintenance |
| [korvo-monitor](../tools/korvo-monitor/README.md) | Korvo provisioning and legacy USB bridge (recovery only) |
| [mission-host](../tools/mission-host/README.md) | Browser lab, planner, and exercise memory (host-side) |
| [survey-simulator](../tools/survey-simulator/README.md) | Host-owned fictional survey session (Node.js) |
| [kulira-core](../tools/kulira-core/README.md) | Seeded chaos-campaign orchestrator (see `tools/kulira-core/README.md`) |
| [fleet-score](../tools/fleet-score/README.md) | Deterministic planner-run scorer (stdlib only; `uv run --project tools/fleet-score python -m pytest tools/fleet-score -q`) |

The mission host and hardware bridges need omitted private inventory and
operator configuration; their READMEs distinguish offline checks from live use.
The browser preview and Node.js survey simulator can run without a fleet.
See [state and source-version compatibility](state-compatibility.md) before
interpreting a preview label as a firmware state or deployment version.

Python is managed with uv, never system pip:

```sh
uv sync --project tools/node-commissioner --group dev
uv run --project tools/node-commissioner python -m pytest tools/node-commissioner/tests -q
```

On SMB/network-mounted workspaces, keep virtualenvs off the mount, e.g.
`UV_PROJECT_ENVIRONMENT="$HOME/.cache/<project>/venv"`.

## Browser preview

```sh
uv run --project tools/node-commissioner python previews/recon-hud/serve.py
# open http://127.0.0.1:8766/
```

Credentials are loaded from a private local store or vault references at
runtime. Nothing secret belongs in this repository; use synthetic
fixtures in tests (see [../SECURITY.md](../SECURITY.md)).
