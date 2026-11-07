# Pre-registration: learned trust under delayed/incomplete feedback (#134)

Status: **pre-registered before this run.** Simulation only.
Reuses `reputation.generate_sequence` unchanged (2 of 8 verified
nodes lie on hazards, 60 contacts, 75% honest accuracy). New
runner: `kulira_core/feedback_trust.py`. Contributor audit:
`docs/research/contributor-notes/feedback-trust-audit.md`.

Question: the reputation result (REP cuts second-half dangerous
commits vs unweighted E) assumes outcomes are revealed after
every contact. How much survives when reveal is delayed by D
contacts, or only a fraction A of outcomes is ever revealed?

## Frozen design

- Policies E, REP, REP-P (as in reputation.py, unchanged).
- Grid: delay D in {0, 5, 15} x availability A in {1.0, 0.5, 0.25}.
- Reveal stream: separate RNG (`seed ^ 0xFEED`), one draw per
  contact. Truth is never used for a decision before its reveal
  event (unit-tested truth boundary).
- Full-feedback cell (D=0, A=1.0) must reproduce
  `reputation.score_sequence` exactly (unit-tested).
- Seeds 220-239 (dev; checked against the exposed-seed ledger:
  0-19, 100-119, 200-219, 300-309, 400-419, 500-509 already used
  in this programme). No confirmatory claim from this split.

## Primary contrast and falsification

- **HF1:** REP at full feedback has fewer second-half dangerous
  commits than E (replication sanity). If this fails, the
  follow-up question is void, not reinterpreted.
- **HF2 (primary):** REP retains an advantage over E at
  (D=15, A=0.25): dangerous_second[REP] < dangerous_second[E].
  Falsified if REP >= E in that cell.
- **HF3:** degradation is monotone-ish: REP dangerous_second at
  (0, 1.0) <= (5, 0.5) <= (15, 0.25). Falsified if the extreme
  cell beats the full-feedback cell.
- Coverage guardrail: report mean decisions and recall beside
  every dangerous count; a "safer" cell that simply commits
  less is named as such, not scored as a win.
