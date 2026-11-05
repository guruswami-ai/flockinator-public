# Flockinator

An experimental platform for intelligent agents and distributed
inference, built and directed with Meta Muse models.

Sixteen independent ESP32-S3 nodes each drive a 64x64, 160x160 mm RGB
panel. Each node is a physical body - sensing, local state, display,
audio, SD storage - whose brain can run locally, on an external host,
or across both. A Korvo-1 (ESP32-S31) controller hosts the fleet controls,
planner, and learning lab; a LilyGo handheld provides portable
management. The fleet is visualised as a fictional search-and-rescue scout swarm
so humans can watch agents learn.

![Flockinator 4x4 grid layout](cad/grid-isometric.png)

## Why

Small models are trained in isolation, then judged by a hostile world.
Kulira, the adversarial host, injects graded friction - interference,
impersonation, and false reports on the experimental channel - so the
swarm must earn trust: validate identity, corroborate independently,
degrade gracefully, recover. It is nature's optimisation story
(hardship and selection) compressed into seeded, reproducible runs,
studying intelligence in the node, external to the node, and between
nodes. Full method and why this is worth doing (security, and the
extra-node intelligence that lives between agents, not inside them):
[docs/experiments.md](docs/experiments.md).

## Meta Muse models

A sixteen-lane Muse swarm (Wonder and Spark tiers, coordinated by
Muse Wonder Full) mirrors the physical swarm: one assessor per node,
sealed evidence, cited claims, canary deployments. Muse models helped
build the firmware, model the 3D hardware, troubleshoot nodes, and
direct the experiments. Evidence and reproduction:
[docs/meta-muse/](docs/meta-muse/README.md).

## Learn the ideas first

New to swarms? [Learn: swarms, shared intelligence, and trust](docs/learn/README.md) - plain-language help pages with pictures, no background needed.

## Explore

| Area | Entry point |
|---|---|
| Architecture and traffic classes | [docs/architecture.md](docs/architecture.md) |
| Experimental methodology | [docs/experiments.md](docs/experiments.md) |
| Results dashboard and methodology | [docs/results/](docs/results/README.md) |
| Illustrated survey scenario | [docs/scenarios/quadcopter-survey/](docs/scenarios/quadcopter-survey/README.md) |
| Proposed sound-and-light flocking scenario | [Patternflow experiment](docs/scenarios/patternflow-flocking/README.md) |
| Hardware, components, finished CAD | [docs/hardware.md](docs/hardware.md), [cad/](cad/README.md) |
| Build and host tools | [docs/build.md](docs/build.md) |
| Firmware | [firmware/node-platform](firmware/node-platform/README.md), [firmware/korvo-monitor](firmware/korvo-monitor/README.md), [firmware/management-console](firmware/management-console/README.md) |
| Browser preview | [previews/recon-hud](previews/recon-hud/README.md) |
| Attack taxonomy and A2A asymmetry | [docs/attack-taxonomy.md](docs/attack-taxonomy.md) |
| Adversary (Kulira) and friction plan | [docs/kulira-friction.md](docs/kulira-friction.md), [tools/kulira-core](tools/kulira-core/README.md) |

## Quick start

```sh
uv run --project tools/node-commissioner python previews/recon-hud/serve.py
# open http://127.0.0.1:8766/
```

## Scope of this repository

A public subset of a private working project: firmware, host tools,
finished 3D models, and experiment design - everything needed to
reproduce the experiments and build the hardware. Private per-node
data (identities, keys, network inventory, raw backups, real-node
journals) and licensed third-party assets are never published here.

## Licence

Apache-2.0 (see [LICENSE](LICENSE)); third-party components retain
their own licences. Contributions: [CONTRIBUTING.md](CONTRIBUTING.md).
Security: [SECURITY.md](SECURITY.md).
