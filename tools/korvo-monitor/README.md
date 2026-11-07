# Korvo host helpers

Host-side roster/Wi-Fi provisioning, authenticated fleet polling and legacy USB
projection for the [Korvo firmware](../../firmware/korvo-monitor/README.md).
The standalone controller is the normal runtime; `bridge.py` is a recovery
helper, not a second controller to run concurrently with it.

From the repository root, use the node commissioner's locked dependencies:

```sh
uv run --locked --project tools/node-commissioner python -m pytest tools/korvo-monitor -q
uv run --locked --project tools/node-commissioner python tools/korvo-monitor/provision_fleet.py --help
uv run --locked --project tools/node-commissioner python tools/korvo-monitor/provision_lab_wifi.py --help
uv run --locked --project tools/node-commissioner python tools/korvo-monitor/bridge.py --help
```

These help/test commands require no controller. They do not establish device
acceptance. Actual provisioning opens USB and changes controller configuration.

## Public-subset boundary

The provisioning helpers contain the redacted controller identity
`00:11:22:33:44:55`; a real deployment must bind the verified controller identity
consistently in host and firmware before use. `bridge.py` also reads omitted
private `docs/inventory/nodes.csv` and `network.csv`, plus identity-bound keys
through [node-commissioner](../node-commissioner/README.md). A clean public clone
cannot poll a fleet without its operator's inventory/configuration.

`provision_fleet.py --port PORT` reads JSON on stdin: exactly sixteen records
with `label`, `ip`, `mac` and `key`, covering A1–D4, or an empty list to retrieve
the current operator PIN. `provision_lab_wifi.py --port PORT` reads `ssid` and
`password` from stdin. Supply these only through a private credential mechanism;
never put keys/passwords in command arguments, source, issues or test fixtures.
Provisioning output can include an operator PIN; do not publish it.

`mission_commands.py`, `mission_dispatch.py` and `mission_projection.py` handle
command validation, acknowledgements and status projection. The legacy labels in
projection are described in the [state compatibility map](../../docs/state-compatibility.md).
A successful authenticated response proves its source and freshness, not that
the simulated observation is true.
