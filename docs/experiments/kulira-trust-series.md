# Kulira trust experiment series: what was measured

Ten seeded lab-simulation experiments, each pre-registered in a
first commit before any code ran, each with published evidence in
`validation/kulira/`. Simulation only throughout: no hardware, no
radio, no on-node inference. Seeds: dev 0-19, holdout 100-109
evaluated once per experiment.

## The arc

| # | Experiment | Question | Headline result |
|---|---|---|---|
| 1 | Relay attack (A/B/C) | Do relayed copies inflate corroboration? | Reporter-counting: 201 forged dangerous commits. Sighting-ID dedup cuts ~4x but **not to zero** (H2 falsified) |
| 2 | Policy D | Verified-origin admission only? | **0 forged-origin commits**, both splits; recall unchanged |
| 3 | Policy E | Add abstention on close calls? | Dangerous -71%; cost: 46% of contacts left Unassessed |
| 4 | Graded sensing | Buy a second look instead? | Recall doubles (0.32->0.68) but dangerous rises - **gate failed**, not recommended |
| 5 | Priority split F | Second looks only where reversible? | E's exact high-priority safety + most recall - **gate passed** |
| 6 | Colluding minorities | Verified nodes lying (valid keys)? | Tolerance threshold **k=1 of 8**; provenance != honesty |
| 7 | Modality betrayal | A sensor type starts lying mid-run? | Modality trust 306->69 dangerous at 0.90 recall; node trust collapses recall (blame pooled at reporter) |
| 8 | Feedback delay | Outcomes arrive late / half missing? | Discount time tracks latency ~1:1; degraded learning still beats none |
| 9 | Composite defence | Do the pieces compose under combined attack? | Dangerous 23->13 post-betrayal, recall **rises**, forged stays 0 - **gate passed** |
| 10 | Reputation defence | Can behaviour suppress verified colluders? | Second-half dangerous ~halved (36->19); reputations separate 0.15 vs 0.74; **cold-start caveat**: slightly worse before history accrues |

## Current recommended stack (each layer measured separately first)

1. **Admission by provenance** - only `direct_verified` sightings
   may decide a commit; unverified and hearsay reports are
   advisory only (bridge Contract v1 auth status).
2. **Commit by margin, abstain on close calls** - contested
   contacts stay explicitly Unassessed for an operator; bought
   second looks only where a commit is reversible.
3. **Weight by learned modality trust** - distrust attaches to
   claim/sensor types, learned from revealed outcomes; reporter
   identity is for provenance, not pooled blame.

## Measured limits (not surprises)

- **Verified collusion** defeats provenance rules: 1 lying insider
  of 8 already lands dangerous commits with honest cooperation.
  Behavioural reputation (experiment 10) suppresses colluders
  after a learning period, but is slightly worse than baseline
  during cold start, and identity-rotating (Sybil) adversaries
  defeat it by construction - untested here.
- **Identify accuracy** bounds everything: at 75% per-sighting
  accuracy, honest error alone produces dangerous commits under
  every voting rule tested. Graded sensing and abstention price
  that bound; they do not remove it.
- **Feedback latency** sizes the exposure window when a modality
  betrays: trust cannot learn faster than truth arrives.

## Relation to the fleet scorecard

The planner candidates in `docs/results/` failed their promotion
gates on judgement at 60-82% identify accuracy. This series is the
adversary-side explanation of *why* judgement is hard, and which
commit/admission rules survive contact with a liar - measured on
the Kulira side, in the same pre-registered, seeded, gated style.
