<!-- Contributor-model draft (muse-spark-1.3-contributor via Meta API, 2026-11-07). Supervisor-reviewed before use; not yet adopted. -->

# Audit: Does Reputation Still Help When Feedback Is Delayed or Incomplete?

**Context audited:** Simulated search robots sharing sightings. Existing result: weighting sightings by reporter track record, learned from outcomes revealed after *every* contact, reduces dangerous false commits in contacts 31-60 of a 60-contact sequence vs. unweighted counting, when 2 of 8 verified reporters systematically lie. Simulated data only.

## 1. Exact incremental question

**How much of the second-half safety benefit survives when outcome labels are DELAYED by D contacts or INCOMPLETE (only fraction p ever revealed)?**

Formally: holding reporters, lie rate (2/8 systematic), sequence length (60), and decision threshold fixed, plot `false commits in 31-60` as a function of `D > 0` and `p < 1.0`.

Why not already answered:
- The existing result assumes immediate, complete supervision: every contact yields a label before the next trust update. It proves reputation *can* learn liars under ideal feedback.
- It does not prove reputation *will* learn in time to help when updates arrive late (weights are stale during early exploitation) or when most contacts yield no update (weights stay near prior).
- Delay and incompleteness could collapse the effect to zero even if the mechanism is correct. That degradation curve is unmeasured.

## 2. Strongest simple baseline to beat

Beat **both**, on the *same* delayed/incomplete stream:

a) **Primary: Unweighted counting with identical threshold.** Counts sightings equally, no learning, no labels needed. This is the correct naive alternative when labels are scarce - it cannot be hurt by delay.

b) **Strict control: Reputation with frozen initial weights.** Same architecture, but weights frozen at uniform before the sequence. This isolates *learning* from static conservatism.

Reputation-under-delay must beat (a) to claim utility, and beat (b) to claim adaptation still occurs. Beating only (b) is insufficient - a uniformly skeptical unweighted rule might be safer and simpler.

## 3. What would falsify "reputation still helps"?

Pre-register on contacts 31-60 only (learning period excluded):

Falsified if, at a given D or p:
- Mean false commits (reputation-delayed/incomplete) >= mean false commits (unweighted), **or**
- Difference in false commits is not sustained after normalizing for commit rate (see below), **or**
- Reputation equals frozen-weights: learning adds nothing once labels are late/sparse.

A single D/p failure does not falsify all; the claim is falsified as a general robustness claim if benefit disappears at modest delay (e.g., D << time needed to identify 2 liars) or modest incompleteness, not only at D~60 or p~0.

## 4. Two confounds to control

**1. Decision coverage: fewer commits ≠ safer.**
Reputation with poor feedback may just become conservative and commit rarely. False commits will fall trivially alongside true finds.
Control: always report pair: `false commits` + `total commits` / `true finds`. Compare precision and recall, not raw false counts. Require: lower false commits at *matched* total commits, or higher precision without collapse in recall.

**2. Update staleness vs. sample count.**
At contact t with delay D, the agent has only t-D labels, not t. Is failure due to *old* information or just *less* information?
Control: yoke a comparison. Condition A: delayed (first t-D labels). Condition B: immediate-but-subsampled to same N updates, but recent. Similarly for incompleteness p: use random missingness, not outcome-dependent missingness, and match total N. If A ≈ B, the issue is sample count, not staleness. If A < B, staleness itself hurts.

**Audit recommendation:** Run D-sweep x p-sweep with fixed seeds, report second-half false commits + commit rate + precision, vs. both baselines above, with N-matched controls.