# Judging entry point — five minutes to the evidence

> **Scope in one breath:** scored results are host planner-simulation
> replay (no on-node inference yet); all planner candidates to date were
> rejected by the frozen gates; "verified" trust labels mean label
> segregation in simulation, not cryptographic proof.

**Flockinator** is a physical instrument for measuring whether
small agents that share information do better than the same agents
alone — and how that sharing breaks under forgery, error, and lies.
Sixteen ESP32 panels make the swarm visible; sealed ground truth
and pre-registered gates make the claims checkable.

## The five-minute path

Short on time? [The demonstration in one page](docs/judging/demo-narrative.md)
connects existing wall footage, one host benchmark, one recorded Meta
review and its checked code change, reproduction and limits.

1. **Watch** the [physical wall footage](https://flockinator-sim.pages.dev/media.html)
   or [narrated demo](https://www.youtube.com/watch?v=HaYNTBhXbu4).
   These show the display instrument, not on-node inference or a continuous
   physical intervention. The [one-page narrative](docs/judging/demo-narrative.md)
   gives the separate host benchmark and recorded review evidence.
2. **Read the scoreboard:**
   [results dashboard](https://guruswami-ai.github.io/flockinator-public/results/)
   and the [claims map](docs/judging/claims-map.md), which grades
   every headline claim by how you can verify it (reproducible /
   frozen / field / private-quoted / unmeasured).
3. **Reproduce something real** (about a minute each):

   ```sh
   # The narrative's one host benchmark, checked against frozen expected content
   uv run python tools/reproduce/run.py --verify

   # Frozen planner baseline, dev seeds 0-19 -> recall 0.2141
   uv run --project tools/fleet-score python tools/fleet-score/baseline.py --seeds 0-19 --out /tmp/bl --label dev

   # A published cycle-07 trust verdict, end to end from journals
   uv run --project tools/fleet-score python tools/fleet-score/gate_runner.py \
     --baseline /tmp/bl/baseline-dev.json \
     --runs docs/results/cycle-07/runs/T3 \
     --config docs/results/cycle-07/verdicts/verdicts-cfg-T3-P0.json \
     --out /tmp/verdict-out

   # The full scorer + gate-runner suite
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
| Panel-policy canary (device parity, pending journal) | [`docs/experiments/panel-policy-canary-preregistration.md`](docs/experiments/panel-policy-canary-preregistration.md), [`validation/kulira/canary-golden-vectors-001.csv`](validation/kulira/canary-golden-vectors-001.csv) — host rehearsal only until a Drishdi device journal is scored |
| Feedback-trust boundary (delayed/sparse reveal) | [`docs/experiments/feedback-trust-confirmatory-results.md`](docs/experiments/feedback-trust-confirmatory-results.md), [`validation/kulira/feedback-trust-paired-001.json`](validation/kulira/feedback-trust-paired-001.json) — simulation, narrowed claim #159 |
| Feedback-trust reporting update (2026-11-07) | [Post hoc supplement](docs/experiments/feedback-trust-reporting-supplement.md) supersedes the [status note's](docs/experiments/feedback-trust-evidence-status.md) reporting gaps; historical verdicts stand, matched-threshold causal study remains future work |
| Firmware build/test provenance | [`docs/firmware-evidence.md`](docs/firmware-evidence.md) |
| What runs where (honestly) | [`docs/judging/physical-execution-map.md`](docs/judging/physical-execution-map.md), [`docs/architecture.md`](docs/architecture.md) |
| Residual problems, named | R1-R9 in [`docs/results/README.md`](docs/results/README.md) |
| Hardware / CAD | [`docs/hardware.md`](docs/hardware.md), [`cad/README.md`](cad/README.md) |

CI (`.github/workflows/ci.yml`) runs both Python suites and checks
the dashboard regenerates byte-identically, so the claims above are
kept honest on every push — not just at freeze time.
