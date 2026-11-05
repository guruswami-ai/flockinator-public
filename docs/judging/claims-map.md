# Claims map — every headline claim, its evidence, and how to check it

One row per claim a judge is likely to repeat. **Class** says how far
you can verify it from this repository alone:

- **R** — reproducible here: the check command or path re-derives it.
- **F** — frozen aggregate: reported from sealed runs; inputs published
  where stated, aggregate itself not re-runnable end-to-end here.
- **H** — hardware field observation (single lab, dated; not a
  controlled trial).
- **P** — private-source quotation: summarized from the private lab
  book / release bundles; not verifiable from this tree.
- **U** — unmeasured / open: explicitly NOT claimed as a result.

## Planner intelligence (simulation replay — never on-node inference)

| Claim | Value | Class | Evidence / check |
|---|---|---|---|
| Frozen baseline sighted recall (`search-board-1`, dev seeds 0-19) | 0.2141 | R | `uv run --project tools/fleet-score python tools/fleet-score/baseline.py --seeds 0-19 --out /tmp/bl --label dev` → mean eligible recall 0.2141 |
| Sector v1 / +confirmation v2 / +adaptive v3 / asymmetric v4 recalls | 0.6226 / 0.6145 / 0.5971 / 0.5971 | F | `docs/results/results-data.json` candidates; candidate journals not bundled (stated in `docs/results/README.md`) |
| Committed Enemy→Friendly per candidate (v2/v3/v4) | 2 / 2 / 1 — all rejected vs gate 0 | F | same file; gate list in `docs/results/README.md` |
| Promotion gates were pre-registered, not edited after results | process claim | F | Gate list + threshold provenance in `docs/results/README.md`; frozen values in `results-data.json` (`gates`) |
| Per-sighting identify accuracy bounds vote policies | 60-82% by cover | R | `COVER` table, `tools/mission-host/planner.py` |
| Holdout seeds 100-109 baseline recall | 0.2055 | F | `results-data.json` `holdout_baseline`; holdout never run for rejected candidates |
| Scorer test suite | 69 tests pass | R | `uv run --project tools/fleet-score python -m pytest tools/fleet-score -q` |

## Trust layer (cycle-07, simulation replay)

| Claim | Value | Class | Evidence / check |
|---|---|---|---|
| Outsider forgery cannot enter a vote (G1) | 61 forged emitted, 0 vote entries | R | `docs/results/cycle-07/` journals + verdicts; re-run via README commands (baseline regen + `gate_runner.py`) |
| Lying insider cannot force a dangerous commit (G4/T3) | 10/10 forced flips → 0 Enemy-committed-Friendly | R | same; `engagement.json` for flip counts |
| Patient liar (T4, turn ≥30) | PASS **vacuous** — 0 engagements | R | `verdicts/annotations.json` (machine-readable vacuity) |
| Hearsay fusion (P1) helps/hurts | — | U | Untested: no hearsay in cycle-07 journals; unit fixtures only |
| Abstention policy (P2) performance | — | U | UNMEASURED by construction in cycle-07 (no scorer column). Kulira's relay series measures related policies in its own harness: `docs/experiments/` |
| Honest baseline vs frozen floors | FAILS (rate 0.0769 vs 0.0750; 13 vs 30 contacts) | R | cycle-07 T0 verdicts; calibration flaw recorded in cycle-07 README |
| Kulira adversary series (10 experiments; composite D+E/F+modality stack) | per-experiment | R/F | `docs/experiments/kulira-trust-series.md` + per-experiment pre-registration/results pairs; code `tools/kulira-core/` (`pytest tools/kulira-core -q`) |

## Hardware / field (2026-11-05 unless stated)

| Claim | Value | Class | Evidence / check |
|---|---|---|---|
| Korvo "associated-but-deaf" wedge + 0.9.1 watchdog bounds it | 12 episodes / 11 tier-1 recoveries at results-freeze count; soak continuing | H | `docs/results/README.md` field section (counting method stated: serial-log watchdog lines × `/api/health` counters); serial log itself is private (carries station identifiers) |
| Restart tier of the watchdog | never fired | H/U | same; design gap named as residual R9 |
| Wedge trigger | unknown | U | residuals R1/R2; router-side evidence outstanding |
| Korvo 0.9.1 binary identity | 2,550,576 B, sha256 `b26c651c…` | P | `docs/firmware-evidence.md` (labelled private quotation; public korvo tree is 0.9.0) |
| Node firmware chain + test counts (141 @0.5.1; 43 native @0.11.x) | per-bundle | P | `docs/firmware-evidence.md` with bundle names; current-tree recounts marked R there |
| Panels keep mission journals on node SD under controller loss | exercised, no loss reported | H | results README field notes; mechanism in `firmware/node-platform` (0.10.2-journal) |
| Speaker fit guide rev2 fits | owner-reported perfect fit 2026-10-28 | H | `cad/speaker-fit-guide/FIRST-PRINT.md` |
| On-node learning / on-node inference by panels | — | U | Explicitly not claimed. Panels render scripted missions; decisions scored are planner-simulation replay (`docs/architecture.md`) |
| Paired gain (comms swarm vs isolated agents, matched budgets) | — | U | Defined in `docs/experiments.md`; no measured row yet anywhere |

## Process claims

| Claim | Class | Evidence |
|---|---|---|
| A model's prose is never deployment authority; canary + gates precede any flash | F (process, artifact-backed) | Intervention chain: [`muse-intervention-chain.md`](muse-intervention-chain.md); zero unsafe promotions across cycles 00-07 |
| Muse lanes assess one node each; routing label is not model proof | F | `docs/meta-muse/README.md` |
| Public tree contains no credentials, keys, device inventory, or legible private screens | R | sanitize greps are re-runnable; hero photo pixelated (PR #47), CAD licensing strip (§ #61/#62/#65) |
