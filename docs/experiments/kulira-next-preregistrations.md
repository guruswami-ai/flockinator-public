# Kulira next experiments — pre-registered, not yet run

Drafted 2026-11-06 with a `muse-spark-1.3-contributor` fleet pass,
then reviewed against the code: every named function below exists in
`tools/kulira-core/kulira_core/` (`colluding.run_colluding`,
`reputation.run_reputation`/`generate_sequence`, composite policies).
Status for all four: **pre-registered, no results yet**. Any run that
deviates from these texts is reported as a deviation, not silently
folded in. Simulated data only, seeded throughout, held-out scoring.


---
# Exp 16 — Selective Silence (Pre-registration)

**Status:** Pre-registered, first commit before any code ran. Simulation only: no hardware, no radio, no on-node inference.

**Question:** Does withholding only helpful true reports force team decisions down to private-only level, and do private-baseline comparison + admission + abstention bound the harm?

## Hypotheses

* **H1 (vulnerability):** Under selective silence, naive pooling falls to ~56.6% team success vs ~72.9% clear, indistinguishable from private-only.
* **H2 (defence):** Private-cue comparison + abstention restores success vs naive pooling under silence, without adding dangerous commits.

## Attack mechanism (legitimate L1/L2/L3 only, simulated seeded data)

Adversary holds valid keys, sends only protocol-valid messages. **Zero false messages.**
* **L1 sense:** senses truthfully, no fabrication.
* **L2 share/relay:** forwards all neutral/unhelpful true reports normally; withholds `direct_verified` true sightings that support the ground-truth commit (*helpful* = would move team vote toward correct). Pure omission/drop.
* **L3 commit/vote:** votes/abstains honestly when asked.
* No forgery, no relay duplication, no Sybil/rotation. 8 nodes, 1 compromised, identify accuracy fixed at 75%.

## Policies compared (all under silence unless noted)

* **P0 Clear:** naive pooling, no adversary (upper bound).
* **P1 Naive pooling + silence** (vulnerable baseline).
* **P2 Private-only:** no sharing (lower baseline).
* **P3 Provenance admission:** only `direct_verified` may decide; rest advisory.
* **P4 P3 + private-cue comparison + strict abstain:** if pooled recommendation contradicts agent private cues or margin < threshold, output `Unassessed` for operator.

## Primary metric

**Team success rate** = fraction contacts correctly committed, paired by seed. Secondary: dangerous commit rate, `Unassessed` rate, reversible-task recall.

## Falsification condition

* **H1 falsified** if P1 is not ≥5pp below P0, or if P1 > P2 +3pp (silence did not force fallback to private).
* **H2 falsified** if P4 − P1 <5pp gain on same seeds, OR P4 dangerous > P1 dangerous, OR P4 `Unassessed` >50% of contacts. No promotion on secondary alone.

## Seeds as replication unit

Each seed = one independent simulated deployment. Dev 0–19 for debug/tuning. Holdout 100–109 run once on frozen code. Report mean + per-seed paired deltas; no pooling across seeds.

## Held-out scoring note

Per seed-use ledger, 0–19 and 100–109 are **design-exposed from Exps 1–15, not fresh holdouts**. This experiment reported as design-exposed evaluation. Promotion requires frozen P4 on new fresh seeds selected after protocol freeze. Evidence: `validation/kulira/exp16_selective_silence/`

---
# Experiment 16: Contradiction / Flip-Flopping — Pre-registration

**Status:** Pre-registered, first commit before any code ran. Evidence to follow in `validation/kulira/16/`.
**Simulation only:** no hardware, no radio, no on-node inference.

## Hypothesis

Under a single credentialed flip-flopper, the current stack (strict composite S) will **oscillate and burn re-checks** on targeted contacts rather than abstain. A contradiction-hold rule will produce hysteresis/abstention: fewer flips, fewer re-checks, more Unassessed on targeted contacts, with no loss of recall on untargeted contacts and no rise in dangerous commits.

## Attack mechanism (legitimate L1/L2/L3 protocol techniques only, simulated data, seeded)

* Swarm: 8 verified nodes per run, 1 attacker (node 0), 7 honest at 0.75 per-sighting accuracy.
* Targets: 10/50 contacts per seed, chosen by seeded RNG.
* Attacker behaviour, targeted contacts only: emit well-formed, valid-key **L1 `REPORT(contact_id, claim)`** alternating `SURVIVOR` / `HAZARD` each turn for up to 4 turns (start side seeded per contact). Untargeted contacts: report honestly.
* Allowed: L1 direct_verified reports only. No forged origin, no Sybil/new IDs, no L2 hearsay inflation, no L3 re-task spoofing/jamming. All ground truth, noise, targets, start sides derived from seed.

## Policies compared

* **A — Strict composite S (baseline):** provenance admission + strict commit/abstain + learned modality trust + reversible-only second looks.
* **B — S + contradiction-hold:** if the same verified source contradicts its own prior L1 claim for the same `contact_id`, freeze contact as `Unassessed/contested`; require corroboration from a second independent verified source before (re)commit; a flip alone triggers no automatic second-look.

## Primary metric

**Oscillation: mean committed-assessment flips per targeted contact** (Survivor↔Hazard or commit→Unassessed→recommit = flip). Secondaries: second-looks/targeted contact, % Unassessed on targeted, dangerous commits, recall on untargeted contacts.

## Falsification condition

Hypothesis is **falsified** if on dev either (i) A flips ≤0.5/targeted contact (no oscillation to fix), or (ii) B fails to cut flips ≥40% *and* re-checks ≥30% vs A, or (iii) B increases dangerous commits vs A or drops untargeted recall >0.05.

## Seeds as replication unit

Each seed = one independent replication (fixed contacts, truth, noise, targets). Report per-seed then mean over split. Dev 0–19 for development. Holdout 100–109 scored once, no tuning.

## Held-out scoring note

Score 100–109 once after freeze, publish dev + holdout. Per seed-use ledger, 0–19 and 100–109 are now **design-exposed, not fresh holdouts** after reuse across Exps 1–15; this run is reported as such. Future candidates must freeze protocol before selecting new evaluation seeds.

---
# Pre-reg: Learning Poisoning — Behavioural Reputation vs Verified Colluders

**Module:** `tools/kulira-core/reputation.py` + composite policy
**Type:** Simulated, seeded, L1/L2/L3-legitimate only

## 1. Hypothesis
Sequential behavioural reputation (REP) will calibrate trust away from persistent liars and reduce dangerous commits in the second half vs. unweighted baseline (E), without collapsing survivor recall. Probationary reputation (REP-P) will retain REP's safety with higher recall.

## 2. Attack mechanism
**LEARNING POISONING — slow-drip bias:** 2 of 8 verified nodes send protocol-valid but false-content sightings during training contacts to mis-calibrate learned trust.

- Only legitimate techniques: L1 signed sightings with valid `sighting_id/node/modality/label`; L2 relay sampling (2-3 nodes/contact) + dedupe by `sighting_id`; L3 composite thresholding. No forgery, spoofing, eclipse, or verification bypass.
- Simulated data, seeded: `random.Random(seed)`, 60 contacts/sequence. Truth ~50% `survivor` / 50% `hazard`.
- If `truth==hazard` and reporter in `COLLUDERS (=NODES[:2])`: label=`survivor`. Else 75% accurate. Modalities sampled from `MODALITIES`.
- Reputation update from revealed outcomes only: `+0.05` if correct, `-0.15` if wrong, clamp `[0.1,1.0]`.

## 3. Policies compared
- **E (egalitarian + abstain):** commit iff `n_surv>=2` and `n_surv-n_haz>=2`.
- **REP:** commit iff `ws>=1.5` and `ws-wh>=1.0`, where `w=rep[node]`.
- **REP-P:** same as REP, except `w=1.0` while `seen[node]<10` (probation).

## 4. Primary metric
**`dangerous_second`:** total dangerous commits (committed when `truth==hazard`) in contacts 30-59, summed over seeds. Secondary: `dangerous_first` (0-29), `mean_recall` (committed/survivor-truth), `rep_colluders` vs `rep_honest`.

## 5. Falsification condition
Hypothesis fails if on frozen seeds: `dangerous_second[REP] >= dangerous_second[E]`, OR `dangerous_second[REP-P] > dangerous_second[REP]`, OR `mean_recall[REP-P] <= mean_recall[REP]`. Any increase in second-half vs first-half dangerous commits for REP also falsifies learning.

## 6. Seeds as replication unit
One seed = one independent 60-contact sequence via `generate_sequence(seed)`. Per-seed scoring via `score_sequence(seq, policy)`, then aggregate by sum (counts) / mean (recall/reputation). No cross-seed learning, no within-sequence reset.

## 7. Held-out scoring note
Tuning only on exploratory seeds. Final evaluation runs `run_reputation(held_out_seeds)` once on frozen, pre-declared held-out seeds with frozen thresholds (`1.5/1.0`, `PROBATION=10`). Report all three policies with per-seed table.

---
## Pre-reg: Coalition with Fresh IDs vs Policy E

**Hypothesis**
H1: Reporter-independent counting falls to credentialed collusion. As colluders `k` 0→3 of 8 verified nodes lie, dangerous commits under Policy E rise monotonically.
H2: Modality-diversity mitigates without killing recall. Policy E-M shows lower dangerous commits than E at same `k`, with mean survivor-recall loss <0.15.

**Attack Mechanism — COALITION WITH FRESH IDS**
Legitimate protocol use only, simulated + seeded. No forgery, no Sybil, no eclipse:
- **L1 — Identity / signatures:** Attackers are `NODES[:k]`, hold valid keys. All sightings well-formed `(sid, node, modality, label)`.
- **L2 — Dissemination:** 1–3 reports/contact via round-robin `NODES[(i+j)%8]`, modality sampled from `MODALITIES`. Each liar mints a distinct `sid = s{i}-{j}` for the same false claim, targeting the defence that counts distinct `sighting IDs, never reporters`.
- **L3 — Trust content:** If `truth==hazard` and reporter in colluders → label `survivor` (verified lie). Otherwise honest with `identify_p=0.75`. No honest-node slander, no replay.

**Policies Compared**
- **E:** Baseline commit from `_commit(reports, "E")` — corroboration by distinct sighting IDs.
- **E-M:** E + `>=2 modalities` required for commit.

**Primary Metric**
Collusion tolerance curve: `dangerous` vs `k` for `ks=(0,1,2,3)`.
`score_colluding()` per trial: `dangerous` = hazard committed as survivor; `colluder_dangerous` = dangerous where deciding set contains a colluder report; `survivor_recall` = committed/survivors. `run_colluding()` sums `dangerous`, `colluder_dangerous` over seeds, means recall. Decision metric is `dangerous_E(k)`; `colluder_dangerous` attributes causality, recall is guardrail.

**Falsification Condition**
H1 falsified if `dangerous_E(2)+dangerous_E(3) <= dangerous_E(0)` summed over pre-reg seeds, or if `colluder_dangerous / dangerous <0.5` at k=2,3 (harm not attacker-driven). H2 falsified if `dangerous_E-M(k) >= dangerous_E(k)` for both k=2,3, or recall drops ≥0.15 vs E.

**Seeds as Replication Unit**
One seed = one 40-contact trial `generate_trial_colluding(seed, k, contacts=40, identify_p=0.75)`. Paired design: same `rng(seed)` contacts/truth for every `k`; only colluder set varies. No within-trial resampling. Report per-seed `score_colluding` then aggregate.

**Held-out Scoring Note**
Dev seeds used for debugging only. Final `run_colluding(seeds, ks)` executed once on pre-declared held-out seeds with frozen `_commit`. Any re-run, added seed, or parameter change reported as deviation, not confirmatory.
