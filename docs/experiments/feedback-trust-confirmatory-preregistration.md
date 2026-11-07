# Pre-registration: feedback-trust confirmatory (seeds 240-259)

Status: **pre-registered before this run.** Simulation only.
Confirms the dev result (seeds 220-239) that learned reputation
under delayed/incomplete feedback becomes worse than not
learning. Runner and world unchanged
(`feedback_trust.py`, `reputation.generate_sequence`).

Frozen subset (kept small): policies E, REP, REP-P; delay
{0, 15} x availability {1.0, 0.25}. Seeds 240-259 fresh.

- **HC1 (primary):** REP dangerous_second at (15, 0.25) >= E
  at the same cell (the dev falsification replicates).
  Confirmatory claim requires REP > E or REP == E with REP-P
  also >= E; if REP < E here, the dev result is withdrawn as
  seed variance.
- **HC2:** REP-P dangerous_second at (15, 0.25) >= 2x E
  (probation collapse replicates). Falsified below 2x.
- **HC3 (sanity):** REP at (0, 1.0) < E. If this fails, the
  whole comparison is void.
- Coverage (decisions, recall) reported per cell as before.

If HC1+HC2 hold, the line closes with the boundary claim:
reputation requires prompt, substantially complete feedback.
If HC1 fails, the dev paper trail stands corrected in public.
