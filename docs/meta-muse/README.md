# Meta Muse models and the Flockinator agent swarm

Flockinator was designed, built, modelled, debugged, and is directed with
Meta Muse models. This page is the hackathon evidence map: which models do
what, how inference flows, and where to verify each claim in this repository.

## Model matrix — sixteen assessors, one coordinator

Sixteen physical ESP32 nodes (A1-D4) are mirrored by sixteen Muse worker
lanes in a 4x4 matrix, one lane per node, plus one coordinator:

| Lanes | Nodes | Model | Effort | Role |
|---|---|---|---|---|
| a1-a4 | A1-A4 | `muse-wonder-1.0` | high | Node evidence assessors |
| b1-b4 | B1-B4 | `muse-spark-1.3` | medium | Node evidence assessors |
| c1-c4 | C1-C4 | `muse-spark-1.2` | medium | Node evidence assessors |
| d1-d4 | D1-D4 | `muse-spark-1.1` | low | Node evidence assessors |
| coordinator | fleet | `muse-wonder-full-1.0` | - | Synthesis, experiment and release decisions |

Other Meta Model API models verified live on this project (2026-11-06):
`sam-3.1` (segmentation comparison in `docs/research/sam-3.1-wall-evaluation.md`)
and `muse-image-1.0` (the rescue-swarm illustration on the public simulation
site; illustrative only, never used as evidence). `muse-voice-transcribe-1.0`
is speech-to-text only; no speech-generation model is listed.

Credentials are injected by the launcher and never stored in this repository. Model IDs and effort are
configured per lane above. Per-assessment request provenance is not yet
published as a citable trace bundle (post-judging backlog), so a routing
label alone is never treated as proof of which model answered.

Why tiered rows: comparing reviewer tiers is itself an experiment. For
evaluator-quality comparisons, identical sealed evidence and a common
rubric go to every tier; node-performance claims never borrow a stronger
reviewer as evidence.

## Inference pipeline

```text
Korvo controller (ESP32-S31, authoritative runtime)
  |  sealed run archives: journals, director truth (kept separate), hashes
  v
Collector (deterministic tool) -- verifies manifests/hashes, publishes
  |  immutable read-only evidence bundles, one per node
  v
16 Muse assessors (Spark/Wonder lanes) -- one node each: cited claims,
  |  observation vs inference separated, retain / adapt / reject proposals
  v
Wonder Full coordinator -- cross-node synthesis, checks citations,
  |  chooses retain / collect-more / candidate / canary; negative and
  |  inconclusive results are first-class outcomes
  v
Isolated build executor -- pinned toolchain, tests, immutable binary+manifest
  v
Single deployment executor -- identity-checked, serialized, canary first,
     readback-verified; a model's prose is never deployment authorisation
```

Rules that keep the pipeline honest:
- Models run remotely; compilers, files, and deployment tools run locally.
  A worker cannot flash its own node or edit another worker's files.
- Evidence is sealed before review. Logs - including adversarial payloads
  from the Kulira chaos experiments - are untrusted data, never instructions.
- A firmware change counts as a behavioural intervention only if that
  firmware actually runs the decision being evaluated.
- Homogeneous and heterogeneous swarms are both evaluated as full
  compositions, not as sixteen independent ratings.

## How Muse models helped build Flockinator

- **Building:** Muse lanes author and review firmware (ESP32-S3 nodes,
  ESP32-S31 Korvo, LilyGo console), host tools, and tests under the
  coordinator, through the isolated build executor above.
- **3D modelling:** Muse assisted the CAD work in `cad/` - panel grid fit,
  acrylic node concept, perimeter speaker carriers, diffuser/print
  validation - generating and checking FreeCAD models and fit reports.
- **Firmware troubleshooting:** tiered assessors diagnose per-node evidence
  (boot, radio, SD, render timing) from sealed logs; the coordinator
  reconciles disagreements against source observations before any fix
  is built or deployed.
- **Directing the swarm:** the coordinator directs the sixteen-lane agent
  swarm that assesses the sixteen-node physical swarm - choosing the next
  experiment, candidate policies, and canary deployments, and stopping
  when evidence is inconclusive.

## Reproduce it

1. Build the hardware/firmware from `firmware/` and `cad/` (see root README).
2. Run an experiment (communication lab / planner) and export its archive.
3. Point sixteen Muse lanes (Spark/Wonder tiers above) at the sealed
   per-node bundles with the assessor prompt in
   [`role-prompts.md`](role-prompts.md); run one Wonder Full coordinator
   over their cited assessments. Keep director truth out of agent inputs
   until scoring.
4. Score with deterministic tools; treat the seed as the replication unit.

Private per-node data (device identities, keys, raw journals from real
nodes) is never published here - only the method, code, models, and
sanitized design evidence needed to reproduce the experiments.
