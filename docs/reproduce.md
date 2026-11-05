# Reproduce the flagship benchmark

One command reproduces Flockinator's flagship communication result
from a clean public checkout. No wall, no lab network, no model
credentials, no private files. Host simulation only.

## Native (no container)

```sh
python3 tools/reproduce/run.py --out /tmp/flockinator-repro
python3 tools/reproduce/run.py --verify   # regression-check vs tools/reproduce/expected.json
```

Python 3.12, standard library only (the wrapper imports the
existing scientific code in `tools/mission-host/`; it does not
copy it). Runtime is under a second on a laptop.

## Container

```sh
docker build -t flockinator-reproduce .
docker run --rm --network none -v /tmp/flockinator-repro:/tmp/out flockinator-reproduce
```

The image copies only the three scientific source files and the
reproduce wrapper, runs as an unprivileged user, and needs no
network at runtime. Build from a public checkout - never from a
private workspace, so no private briefs, journals, footage, or
credentials can enter the image (`.dockerignore` plus explicit
`COPY` paths).

## Expected output

```
Clear peer messages:      72.949% (1494/2048 team tasks)
Private cues only (muted): 56.641% (1160/2048)
Scrambled peer messages:   33.594% (688/2048)
```

Team success means at least 3 of 4 agents in a team choose the
correct sector (4 teams x 32 held-out rounds per seed; team tasks
within a seed are not independent experiments). Outputs:
`results.json` (per-seed counts and rates; canonical scientific
content hashed with sha256) and `summary.txt`. Reproducing these
numbers is a regression check on the shipped algorithm, not a
new independent confirmation.

## Limitations

- The muted/private baseline receives no peer messages by design;
  its information budget differs. The comparison isolates the
  value (and danger) of peer messages, not communication at
  matched information.
- Host simulation only: not on-node learning, not physical-swarm
  advantage, not rescue capability.
- Container validated in CI on linux/amd64 (ubuntu-latest).
  arm64 is untested, not claimed.
