# Proposal (NOT registered): matched-control follow-up to #159

Status: **proposal for owner protocol review. Not a
pre-registration. No seeds selected, no run performed.**
Seeds 220-259 are exposed and must not be reused for any
confirmatory claim from this design.

## Why

The #159 correction established that REP vs E does not
isolate learning: E commits at count margin >=2, REP at
weighted margin >=1. The post hoc frozen-weight diagnostic
on exposed seeds (frozen 91/83 vs learned 45/38 second-half
dangerous) suggests learning helps its own configuration,
but it is post hoc and cannot become a claim.

## Proposed design (for review, not adoption)

- Arms, all on identical generated sequences:
  1. REP learned (as shipped).
  2. REP frozen at unit weights (availability 0) — the
     matched no-learning control at REP thresholds.
  3. REP with thresholds matched to E (weighted margin
     >=2) — isolates the threshold difference itself.
  4. E (as shipped) as the external reference.
- Grid: the two cells that matter — (D=0, A=1.0) sanity and
  (D=15, A=0.25) extreme — not a new full grid.
- Seeds: fresh, drawn and committed in the registration
  commit itself, in their own commit before any evidence
  file exists (chronology must be inspectable).
- Endpoint declared before running: second-half dangerous
  commits AND second-half commits/true-survivor recall on
  the same window, with an explicit harm/recall objective
  weighting chosen by the owner at review. Paired per-seed
  reporting; no interval criterion smuggled in afterwards —
  the acceptance rule is whatever the registration states.

## Acceptance gate

Owner reviews this proposal and either (a) approves a
separate registration commit, (b) edits the arm set or
objective, or (c) declines. Until then: no code, no seeds,
no claim changes. The #159 narrowed boundary claim stands
as-is in the meantime.
