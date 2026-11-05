# Judging entry point — five minutes to the evidence

**Flockinator** is a physical instrument for measuring whether
small agents that share information do better than the same agents
alone — and how that sharing breaks under forgery, error, and lies.
Sixteen ESP32 panels make the swarm visible; sealed ground truth
and pre-registered gates make the claims checkable.

## The five-minute path

1. **Watch** the narrated demo (linked from the
   [README](README.md)) — what the wall is and why it exists.
2. **Read the scoreboard:**
   [results dashboard](https://guruswami-ai.github.io/flockinator-public/results/)
   and the [claims map](docs/judging/claims-map.md), which grades
   every headline claim by how you can verify it (reproducible /
   frozen / field / private-quoted / unmeasured).
3. **Reproduce something real** (about a minute each):

   ```sh
   # Frozen planner baseline, dev seeds 0-19 -> recall 0.2141
   uv run --project tools/fleet-score python tools/fleet-score/baseline.py --seeds 0-19 --out /tmp/bl --label dev

   # A published cycle-07 trust verdict, end to end from journals
   uv run --project tools/fleet-score python tools/fleet-score/gate_runner.py \
     --baseline /tmp/bl/baseline-dev.json \
     --runs docs/results/cycle-07/runs/T3 \
     --config docs/results/cycle-07/verdicts/verdicts-cfg-T3-P0.json \
     --out /tmp/verdict-out

   # The full scorer + gate-runner suite (69 tests)
   uv run --project tools/fleet-score python -m pytest tools/fleet-score -q

   # Kulira adversary suite
   uv run --project tools/kulira-core python -m pytest tools/kulira-core -q
   ```

4. **See the method bite:** one complete
   [Muse intervention chain](docs/judging/muse-intervention-chain.md) —
   a gate runner returned for a wrong rate denominator, a matrix
   held for label drift, a vacuous PASS labelled instead of
   rescued, a holdout kept sealed.
5. **Check what is NOT claimed:**
   [physical execution map](docs/judging/physical-execution-map.md) —
   decisions are simulation replay, panels do not (yet) decide live,
   and the demo bridge is labelled replay.

## Where things live

| Want | Go to |
|---|---|
| Every claim + verification route | [`docs/judging/claims-map.md`](docs/judging/claims-map.md) |
| Planner scorecard + methodology | [`docs/results/README.md`](docs/results/README.md) |
| Trust-layer dev matrix (journals, verdicts) | [`docs/results/cycle-07/`](docs/results/cycle-07/README.md) |
| Adversary experiment series | [`docs/experiments/`](docs/experiments/kulira-trust-series.md), [`tools/kulira-core/`](tools/kulira-core/README.md) |
| Firmware build/test provenance | [`docs/firmware-evidence.md`](docs/firmware-evidence.md) |
| What runs where (honestly) | [`docs/judging/physical-execution-map.md`](docs/judging/physical-execution-map.md), [`docs/architecture.md`](docs/architecture.md) |
| Residual problems, named | R1-R9 in [`docs/results/README.md`](docs/results/README.md) |
| Hardware / CAD | [`docs/hardware.md`](docs/hardware.md), [`cad/README.md`](cad/README.md) |

CI (`.github/workflows/ci.yml`) runs both Python suites and checks
the dashboard regenerates byte-identically, so the claims above are
kept honest on every push — not just at freeze time.
