# Mission host

Desktop host for scripted mission presentation, the communication-learning lab,
planner and exercise journals. This is distinct from the standalone Korvo
implementation. Agents, energy and locations are simulated; copying journals to
panels does not establish on-panel learning.

## Offline checks

From the repository root, with a C++17 compiler named `c++`:

```sh
uv run --locked --project tools/node-commissioner python -m pytest tools/mission-host -q
c++ -std=c++17 -shared -fPIC tools/mission-host/world.cpp -o /tmp/flockinator-world.so
uv run --locked --project tools/node-commissioner python tools/mission-host/host.py --help
```

`world.cpp` reuses the node's scripted timeline and coordinates. Keep the sibling
firmware tree. Tests use temporary stores and mocked clients; they do not send
commands to hardware.

## Runtime dependencies

`host.py --library /tmp/flockinator-world.so` serves the browser on loopback port
8782 (`--port` overrides it). It requires private `docs/inventory/network.csv`
and `nodes.csv`, all sixteen labels, and commissioner credentials. These are
omitted from the public subset, so this command is **not a standalone public
demo launch**. Once configured it starts fleet polling; browser mission actions
can command real panels. Use [the preview](../../previews/recon-hud/README.md)
or [survey simulator](../survey-simulator/README.md) for a hardware-free display.

The `--data` path defaults to `~/.local/share/flockinator/mission.json`; related
planner state and run archives are kept beside it. Use private storage for any
real fleet data. `prop.py` connects the legacy USB controller to this host;
`read_card.py` retrieves a node's journal using a receipt. Both require deployment
configuration and are not needed for the offline tests.

`planner.py`, `coordination_lab.py` and `exercise_memory.py` provide the host
model used by the [fleet scorer](../fleet-score/README.md) and separate
experiments. Reproduction results establish the stated simulation only.
