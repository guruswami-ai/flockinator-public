# Fictional survey simulator

A local Node.js session server with a browser view, bounded simulation clock and
exportable deterministic replay. It uses Node's built-in modules; there is no npm
installation step. From the repository root:

```sh
node tools/survey-simulator/server.mjs --host 127.0.0.1 --port 8767
# Open http://127.0.0.1:8767/
```

The server binds loopback, validates local origins and serves assets from
`previews/recon-hud`. Keep those sibling files. It stores a monotonically
increasing run counter in `~/.local/share/flockinator/survey-session.json`;
this is session bookkeeping, not a scientific seed registry. Stop with Ctrl-C.

Export the running session and verify its recorded commands/snapshots:

```sh
curl --fail http://127.0.0.1:8767/api/replay -o /tmp/flockinator-survey-replay.json
node tools/survey-simulator/replay.mjs --input /tmp/flockinator-survey-replay.json --verify
```

A successful replay proves internal reproducibility of that session, not physical
behaviour, sensor accuracy or the quality of a policy. The public subset does
not include the original simulator test harness. Syntax checks are available:

```sh
node --check tools/survey-simulator/server.mjs
node --check tools/survey-simulator/engine.mjs
node --check tools/survey-simulator/session.mjs
```

`bridge.py` is a separate **hardware** adapter, not part of this offline launch.
It requires omitted private inventory and commissioner credentials. Its
`--take-control` option changes named nodes to survey mode; do not run it to
verify the browser. See [build/tool boundaries](../../docs/build.md).
