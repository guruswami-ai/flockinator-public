# Flockinator

A visually compelling experimental platform for intelligent agents and
distributed inference - built with Meta Muse models for the Meta hackathon.

Sixteen independent ESP32-S3 nodes each drive a 64x64 pixel, 160x160 mm RGB
panel. They sense, retain local state, communicate, and act as members of a
swarm. They do not form one logical or visual screen. Each node is a physical
body; its brain can run locally, on an external CPU/GPU system, or across
both. An ESP32-S31 Korvo controller hosts the web controls, tabletop planner,
communication/learning lab, and experiment archives; a LilyGo handheld
provides portable management.

## Explore the visual guide

[**Reading the swarm — illustrated field guide**](https://guruswami-ai.github.io/flockinator-public/)

Follow a quadcopter survey rehearsal through 25 panel states, an illustrated
mission timeline, a conceptual decision tree, and paired communication flashes.
The guide explains each display and distinguishes scripted presentation from
measured communication and learning. Read the
[full scenario documentation](docs/scenarios/quadcopter-survey/README.md)
or [watch the project video](https://youtu.be/C9KMvd3-J5c).

## Meta Muse models at the centre

Flockinator is directed by a swarm of Meta Muse models mirroring the
physical swarm: sixteen Muse assessor lanes (Wonder and Spark tiers), one
per node, coordinated by Muse Wonder Full. Muse models helped build the
firmware, model the 3D hardware, troubleshoot per-node evidence, and direct
the agentic swarm's experiments. See
[docs/meta-muse/](docs/meta-muse/README.md) for the model matrix, inference
pipeline, role prompts, and how to reproduce it.

Highlights:
- **Learning under adversity:** small models train in isolation and improve
  under graded friction - disruption, impersonation, and false reports -
  injected by a bounded adversary (`kulira-core`, `SPEC-kulira-core.md`).
  Intelligence is studied in the node, external to the node, and between nodes.
- **Controlled experiments:** seeded, replayable runs; director truth kept
  separate from agent inputs; communication-lab evidence that message
  *meaning* - not packet volume - drives learning.
- **Real hardware:** firmware in `firmware/`, 3D-printable models in `cad/`,
  browser previews in `previews/`, host tools in `tools/`.

## Measured results — the self-improving loop

Four planner-intelligence generations, pre-registered safety gates,
three honest rejections and zero unsafe promotions, charted in
[`docs/results/`](docs/results/) (GitHub Pages: `docs/results/`).
Coverage nearly tripled (recall 0.2141 → 0.6226); committed
Enemy→Friendly stays gated at zero, and no sighting-count voting rule
has met it at useful yield yet — the dashboard shows exactly where
each candidate failed, and the deterministic scorer plus sample
journals let you reproduce every number and try to beat it.

## Reproduce

```sh
# experiment results (scorer + charts)
python3 tools/fleet-score/score.py docs/results/sample-runs/baseline-seed-10
python3 -m unittest discover -s tools/fleet-score -p 'test_*.py'
python3 docs/results/generate_dashboard.py

# browser preview
uv run --project tools/node-commissioner python previews/recon-hud/serve.py
# open http://127.0.0.1:8766/

# tests
node --test validation/recon-hud/*.test.mjs 2>/dev/null || true
uv run --project tools/kulira-core python -m pytest tools/kulira-core -q
```

Firmware build/flash commands, board details, and acceptance checks are in
each `firmware/*/README.md`. CAD sources and print validation are in `cad/`.

## What is not here

This public repository is a sanitized subset of a private working repository.
Private per-node data - device identities and keys, MAC/IP inventory, raw
flash/SD backups, and journals derived from real nodes - is never published.
People can reproduce the experiments and build the hardware from what is
here; the private operational data stays private. Purchased/licensed
reference models and third-party assets are likewise excluded and must be
obtained from their original sources.

## Licence

Apache-2.0 - see [LICENSE](LICENSE). Documentation and design material are
provided for reproduction of the experiments; third-party dependencies
retain their own licences (recreate them from the pinned manifests).
