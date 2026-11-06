# Results (DEV): selective silence

Status: **exploratory dev run, seeds 0-15 — not the confirmatory
held-out run** pre-registered in
[kulira-next-preregistrations.md](kulira-next-preregistrations.md).
Evidence: `validation/kulira/selective-silence-dev-001.json`.
Module: `tools/kulira-core/kulira_core/selective_silence.py`
(tests: `test_selective_silence.py`, 4 passed).

The adversary forges nothing and adds nothing: on half the hazard
contacts it deletes the honest hazard sightings, leaving only
survivor-labelled honest errors visible.

| Policy | Dangerous | Of which suppression-pivotal | Survivor recall |
|---|---|---|---|
| A reporter-count | 11 | 0 | 0.449 |
| B sighting-id dedup | 11 | 0 | 0.449 |
| C multi-modal + multi-node | 9 | 0 | 0.329 |
| D verified-only | 11 | 0 | 0.449 |
| E verified + margin abstention | 5 | 2 | 0.310 |
| E-M E + >=2 modalities | 3 | 1 | 0.244 |

Reading (dev seeds only): dedup and verified-only change nothing
against silence, as pre-registered H2 predicted — there is nothing
forged to filter. Margin abstention and modality diversity cut
dangerous commits by more than half at a clear recall cost. The
surprise is attribution: under A, **zero** dangerous commits were
suppression-pivotal — restoring the suppressed sightings still
commits, because with 1-3 reports per contact the honest error
majority often suffices on its own. Suppression becomes pivotal
mainly under the stricter policies (2 of E's 5). Silence, at this
report density, is an amplifier of honest error more than an
independent cause — a dev-seed observation the confirmatory run
must test, not a conclusion.
