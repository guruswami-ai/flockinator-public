# Reassessment follow-ups: proposals for Drishdi-owned areas

Kulira-authored proposals only. No firmware, planner, or
fleet-score files are modified here. Each item names the owner
whose process should implement and review it. Written after the
2026-11-07 public reassessment; PR #127 (gate-side WF fixes)
is the companion code change awaiting Drishdi review.

## P5 - Response authenticity (firmware/commissioning owner)

Finding: requests are authenticated (per-device HMAC
challenge-response) but an unsigned fabricated status response
was accepted by a harness using production acceptance
functions, marking a node live.

Proposal (design, for the owner's pre-registration):
- Bind every management response to its request: response tag =
  HMAC(device_key, request_nonce || node_id || status_payload),
  truncated consistently with the existing wire tag practice.
- Node/coordinator acceptance requires: tag valid, nonce equals
  the outstanding request nonce, node id equals the addressed
  node, and monotonic status sequence where available.
- Negative fixtures before any deployment claim: unsigned
  response, altered payload with original tag, replayed
  response to a new nonce, response from node A presented as
  node B, stale-nonce response. Valid response must still pass.
- Until this lands, status responses must not be cited as
  deployment evidence (the reassessment's own instruction).

## P4 - Fresh-builder credential path (commissioning/docs owner)

Finding: a new builder cannot initialise fleet credentials;
docs describe vault import or copying an existing private
store, and first-time identity creation expects records.

Proposal (from contributor plan, supervisor-reviewed):
- A documented `init` flow that generates a builder's OWN fleet
  keys locally: master key generated on the builder's machine,
  per-node keys derived/issued at first (wired) flashing, store
  at 0600, never inside any repository.
- CLI surface: `init` (create store), `add-node` (issue one
  node's record), `list --count-only` (no values printed).
- Acceptance test: clean environment with no vault executable
  and no owner records can initialise a synthetic fleet and run
  the host experiment end to end.
- Documentation must say plainly: owner keys are never shared;
  every builder generates their own.

## P2b - COMP replay labelling (experiment/site owner)

Finding: the COMP replay changes both modality weighting and
commit thresholds but is labelled for weighting only; its
stored run has 1 hazardous commit under the baseline policy
and 2 under COMP.

Proposal: name composite comparisons for every changed
component ("modality weighting + stricter commit thresholds"),
and print both outcome counts in the results line, including
when the composite is worse. A composite that wins should have
to win with its costs visible; one that loses should be
reported as a negative result, as this programme does
elsewhere.

## P6 - Rotation reconciliation (analysis; commitment owner)

The two simulator families disagree on rotation (null in
operations regimes, beneficial at fixed count in the commitment
model). Cheapest decisive step is matched-controls analysis
across both models on shared scenarios - no hardware, no new
seed claims. Kulira has documented the contradiction in
`docs/experiments/operations-commitment-index.md`; running the
reconciliation needs the commitment model's owner.

## Status of Kulira-side items

- Canary contract alignment, parity correctness, SIM context
  rejection: merged (PR #126).
- WF gate fixes: PR #127, awaiting Drishdi review; not merged
  by Kulira.
- Meta bundle 001: merged; future bundles must archive raw API
  envelopes at call time (process fix recorded in the bundle).
