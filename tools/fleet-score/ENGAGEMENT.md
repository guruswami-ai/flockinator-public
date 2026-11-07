# Prospective treatment-engagement audit

`engagement.py` supports the remaining measurement work in
[issue #129](https://github.com/guruswami-ai/flockinator-public/issues/129).
It is an **additive instrumentation checker**, not a new gate set, a registered
experiment, or proof of policy benefit. `score.py` stays at version 4 and the
historical gate runner and result archives are unchanged.

A policy can commit without ever meeting the treated node. Conversely, a
real intervention can occur while every policy abstains. Commit counts therefore
cannot establish whether a liar treatment was exercised. A wrong label alone
also cannot distinguish a forced label from an ordinary sensor error.

## Input contract: `flockinator-treatment-evidence/1`

One JSON file per run/seed, emitted contemporaneously by the simulator at its
label-intervention boundary. Include **all acquired observations**, including
unaffected nodes, early observations and non-hazard contacts. Use these fields:

| Field | Meaning |
|---|---|
| `schema` | Exactly `flockinator-treatment-evidence/1` |
| `run`, `seed` | Nonempty run identifier and nonnegative integer seed |
| `treatment` | `T3` (immediate liar) or `T4` (delayed liar) |
| `designated_unit` | Nonempty identifier of the treated node |
| `start_turn` | Nonnegative inclusive activation turn; must be 0 for T3 |
| `complete` | Boolean producer attestation that the full run observation stream is present |
| `observations` | List of records; an explicitly complete empty list means no observations |

Each observation has a unique nonempty `id`, nonempty `unit`, integer `turn`
>= 0, `truth`, `untreated_label`, `treated_label`, and boolean `applied`.
The three label fields use `hazard` or `survivor` (historical Enemy/Friendly).
`untreated_label` must be captured immediately before the treatment assignment
on the **same observation**, not inferred from truth or a separately rerun
counterfactual. `applied` records execution of that assignment even when the
pre-treatment label was already `survivor`.

An opportunity is an observation from the designated node, of a true hazard,
at or after `start_turn`. An applied intervention must be at such an opportunity
and its resulting label must be `survivor`. An unapplied intervention must leave
the label unchanged. Duplicate IDs, malformed values, or contradictions reject
the input. Unrecognised extra fields do not influence counts; in particular,
`commits` is ignored. These checks enforce internal consistency, not authenticity.

## Usage and interpretation

From the repository root, after saving instrumentation to a separate path:

```sh
uv run --no-project python tools/fleet-score/engagement.py /tmp/evidence.json
```

The command only reads the input and prints a `flockinator-engagement-audit/1`
JSON object. It never writes a verdict file or overwrites historical evidence.

| Status | Meaning | Exit |
|---|---|---|
| `ENGAGED` | Complete evidence has at least one eligible applied intervention | 0 |
| `NO_OPPORTUNITY` | Complete evidence has zero eligible observations | 2 |
| `NOT_EXERCISED` | Complete evidence has opportunities but no applied intervention | 2 |
| `UNMEASURED` | Producer explicitly marks the evidence incomplete | 2 |
| `ERROR` | Missing/unreadable/malformed evidence or inconsistent records | 3 |

Output includes opportunities, assignments applied and labels actually changed;
these are separate quantities. Incomplete evidence can have positive counters
but never establishes engagement. `ENGAGED` is not PASS: one applied assignment
may be below the eventual preregistered engagement floor, may change no label,
and says nothing about dangerous decisions, recall or statistical power.

## Integration boundary

Before prospective collection, the experiment owner must wire this contract to
the simulator's intervention point, verify completeness against the source
observation stream, and bind run/seed/source revision and hashes in a manifest.
The caller must check this identity against the scored run rather than accepting
an arbitrary sidecar. Keep truth and pre-treatment labels outside policy inputs.
A future versioned gate set must specify per-seed/pooled engagement floors,
missing-evidence handling and decision rules before outcomes are inspected.
This checker deliberately does not combine evidence across seeds or silently
change G4.

Cycle-07's existing `engagement.json` and journals have different, frozen
semantics. Do not retrofit `applied=true` from their wrong labels or claim they
satisfy this new contract. Their published vacuity annotations remain relevant.
No scientific runs, new seeds, firmware or device actions are needed to test
this utility; the test suite uses constructed fixtures only.
