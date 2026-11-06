# Results (DEV): flip-flopping credentialed source

Status: **exploratory dev run, seeds 0-15 — not the confirmatory
held-out run** pre-registered in
[kulira-next-preregistrations.md](kulira-next-preregistrations.md).
Evidence: `validation/kulira/flipflop-dev-001.json`. Module:
`tools/kulira-core/kulira_core/flipflop.py` (tests:
`test_flipflop.py`, 3 passed).

After contact 30, one credentialed source (A1/ir) alternates its
alarm every contact regardless of truth. All other readings and the
trust update (+0.10/-0.15, clamped) are the modality-betrayal world.

| Latch (drop, restore) | Dangerous / hazards | Median decision flips (of 29) | Mean rechecks | Latched seeds |
|---|---|---|---|---|
| (1,1) | 90 / 252 | 17 | 3.38 | 6 |
| (2,2) | 91 / 252 | 16 | 3.44 | 3 |
| (3,2) | 91 / 252 | 16 | 3.44 | 1 |
| (3,4) | 91 / 252 | 16 | 3.44 | 1 |
| (5,5) | 92 / 252 | 16 | 3.50 | 0 |

Reading (dev seeds only): the dispatch decision flaps on roughly
half of all post-onset transitions under **every** latch setting, and
the persistence latch is not the cure — it barely engages. A
flip-flopping source agrees about half the time, so its trust hovers
mid-range and rarely stays below the 0.30 latch threshold for D
consecutive contacts; raising D only makes engagement rarer (6 -> 0
latched seeds) without reducing flips, dangerous commits, or recall
(0.965-0.980 throughout). Level-based trust cannot see oscillation;
the signal is in the *variance* of agreement, not its mean. A
variance-aware trust penalty (discount on alternation rate, not on
trust level) is the follow-up the confirmatory design should
pre-register. Recheck burn is low (about 3.4 contacts per seed where
the flipper alone swung the decision) — the cost of flip-flopping
here is pervasive indecision, not wasted verification.
