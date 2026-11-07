#!/usr/bin/env python3
"""Deterministic scorer for flockinator planner journal runs.

Reads one run directory (per-unit ``*.jsonl`` journals plus
``director.json`` ground truth) and computes the balanced scorecard from
docs/design/self-improving-firmware-loop.md. Stdlib only.

Definitions are deliberately plain counts; interpretation lives in cycle
reports, not here. ``contact`` in journal events is a 1-based index into
the director's ``ground_truth`` list (verified against tile positions;
a mismatch raises instead of silently scoring garbage).

Cycle-07 stage-1 auth model (v4; Amendment 1): events may carry
``auth_status`` in {direct_verified, hearsay_relayed, unverified,
forged_rejected} (plus step-2 ``claimed_sender``/``l2_source``/
``origin_turn``). Only ``direct_verified`` sightings vote
(P0 ignore-unverified); journals without auth fields default to
``direct_verified`` so legacy runs score identically on pre-existing
fields. Trust boundary, explicit: segregation applies to journals
that carry auth fields; unauthenticated legacy journals are trusted
by definition (scored exactly as v2) and must not be mixed into a
trust-policy run.
Amendment 1 filtering: any event whose ``auth_status`` is present and
not ``direct_verified`` is excluded from every scoring input except
the auth census and the forged-pressure counters. ``forged_rejected``
(and any unrecognized or non-string status) never reaches
``contact_of`` and never counts as a sighting.

Usage: python3 score.py <run-dir> [--markdown]
"""
import collections
import json
import pathlib
import sys

HOME = (7, 11)
SCORER_VERSION = 4

# Stage-1 vote eligibility (cycle-07 pre-reg P0 + Amendment 1): only direct
# sightings vote. Non-scoring events (auth present and not direct_verified)
# are excluded from every scoring input except the auth census and the
# forged-pressure counters.
AUTH_ORDER = ("direct_verified", "hearsay_relayed", "unverified",
              "forged_rejected")
LEGACY_AUTH_DEFAULT = "direct_verified"  # missing field = honest baseline
VOTE_ELIGIBLE = frozenset({"direct_verified"})
# Fusible without voting alone (P1 precondition needs direct support).
FUSIBLE = frozenset({"direct_verified", "hearsay_relayed", "unverified"})
INVALID_AUTH_BUCKET = "invalid_auth_status"  # non-string auth_status lands here


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else None


def _load(run_dir: pathlib.Path):
    director = json.loads((run_dir / "director.json").read_text())
    events = []
    for path in sorted(run_dir.glob("*.jsonl")):
        for line in path.read_text().splitlines():
            if line.strip():
                events.append(json.loads(line))
    if not events:
        raise ValueError(f"no journal events under {run_dir}")
    return director, events


def score_run(run_dir) -> dict:
    run_dir = pathlib.Path(run_dir)
    director, events = _load(run_dir)
    truth = director["ground_truth"]

    def _contact_index(contact):
        # bool is not a contact index (True is not contact 1).
        if isinstance(contact, bool) or not isinstance(contact, int):
            return None
        if not 1 <= contact <= len(truth):
            return None
        return contact - 1

    def contact_of(ev):
        idx = _contact_index(ev.get("contact"))
        if idx is None:
            raise ValueError(
                f"invalid contact index {ev.get('contact')!r} in event {ev!r}")
        entry = truth[idx]
        if list(entry["pos"]) != list(ev["tile"]):
            raise ValueError(
                f"contact {ev['contact']} tile {ev['tile']} != ground "
                f"truth pos {entry['pos']} (run {ev.get('run')})")
        return idx, entry

    def _auth_norm(ev):
        # Missing field = legacy honest default. Non-string values fail
        # closed into a fixed bucket (never crash, never vote).
        if "auth_status" not in ev:
            return LEGACY_AUTH_DEFAULT
        v = ev["auth_status"]
        return v if isinstance(v, str) else INVALID_AUTH_BUCKET

    def _scores(ev):
        # Amendment 1.3 scorer-side filtering: an event carrying auth_status
        # scores only when direct_verified. Legacy events score exactly as v2.
        return "auth_status" not in ev or ev["auth_status"] == "direct_verified"

    scoring = [ev for ev in events if _scores(ev)]
    # Finding-2 fix: units with no scoring events are not fleet units.
    units = sorted({ev["unit"] for ev in scoring})
    # Census scope is pinned to sighting reports (discoveries) for stage 1.
    raw_discoveries = [ev for ev in events if ev["event"] == "discovery"]

    # Deterministic auth census over discovery events. All four enum keys
    # are always present (zeros included); unexpected string values append
    # sorted; non-string values share the invalid bucket above.
    _auth_counts = collections.Counter(_auth_norm(ev) for ev in raw_discoveries)
    reports_by_auth_status = {k: _auth_counts.get(k, 0) for k in AUTH_ORDER}
    for k in sorted(_auth_counts):
        if k not in reports_by_auth_status:
            reports_by_auth_status[k] = _auth_counts[k]

    # Segregation BEFORE contact_of: only direct_verified sightings vote.
    # forged_rejected, unrecognized, and non-string statuses never reach
    # contact_of, never count as sightings, and never crash the tile check.
    discoveries = [ev for ev in raw_discoveries
                   if _auth_norm(ev) in VOTE_ELIGIBLE]

    def _lenient_index(ev):
        # Vote-shaped check that never raises: valid contact whose tile
        # matches ground truth. Used for pressure counters and fusions;
        # never a substitute for contact_of.
        idx = _contact_index(ev.get("contact"))
        if idx is None:
            return None
        tile = ev.get("tile")
        # Rejected/non-voting reports may contain arbitrary JSON. Scalars
        # and objects are not coordinates and must not crash this census.
        if not isinstance(tile, (list, tuple)):
            return None
        if list(truth[idx]["pos"]) != list(tile):
            return None
        return idx

    forged_events = [ev for ev in raw_discoveries
                     if _auth_norm(ev) == "forged_rejected"]
    # Amendment 1.1 split. forged_vote_entries is the G1 quantity: forged
    # sightings entering any vote tally (0 by segregation; nonzero means
    # the partition broke). forged_vote_shaped_attempts is the pressure
    # metric: well-formed forgeries that would have voted down the naive
    # (v2) path. Malformed forgeries count in the census above only.
    forged_vote_entries = sum(1 for ev in discoveries
                              if _auth_norm(ev) == "forged_rejected")
    forged_vote_shaped_attempts = sum(
        1 for ev in forged_events if _lenient_index(ev) is not None)
    found = {}           # contact idx -> set of units
    mislabelled = 0
    enemy_as_friendly = 0
    friendly_as_enemy = 0
    truth_kind_discoveries = collections.Counter()
    per_unit_found = collections.Counter()
    for ev in discoveries:
        idx, entry = contact_of(ev)
        found.setdefault(idx, set()).add(ev["unit"])
        per_unit_found[ev["unit"]] += 1
        truth_kind_discoveries[entry["kind"]] += 1
        if ev["reported_label"] != entry["kind"]:
            mislabelled += 1
            if entry["kind"] == "Enemy":
                enemy_as_friendly += 1
            else:
                friendly_as_enemy += 1

    # Majority-fusion assessment, computed identically for every ruleset:
    # a contact's assessed label is the strict majority of its sightings;
    # "confirmed" additionally requires at least two sightings.
    labels_by_contact = collections.defaultdict(collections.Counter)
    for ev in discoveries:
        idx, _ = contact_of(ev)
        labels_by_contact[idx][ev["reported_label"]] += 1

    def majority(counter):
        ranked = counter.most_common()
        if ranked and (len(ranked) == 1 or ranked[0][1] > ranked[1][1]):
            return ranked[0][0]
        return None

    def _asym_commit(counter):
        # Frozen cycle-06 rule, shared by direct / inclusive / P1 paths so
        # the three cannot drift apart.
        label = majority(counter)
        total = sum(counter.values())
        if total >= 3 and label == "Enemy":
            return "Enemy"
        if counter.get("Friendly", 0) >= 3 and (
                total == counter["Friendly"]
                or (total >= 5 and total - counter["Friendly"] <= 1)):
            return "Friendly"
        return None

    assessed = {}      # idx -> majority label, >=1 sighting
    confirmed = {}     # idx -> majority label, >=2 sightings
    committed3 = {}    # idx -> majority label, >=3 sightings
    # Asymmetric commit (cycle-06 pre-registration): committing the
    # dangerous-direction label Friendly costs more evidence than Enemy.
    # Enemy: >=3 sightings, strict majority. Friendly: >=3 unanimous,
    # or >=5 sightings with at most 1 non-Friendly. Anything else
    # (incl. other majority labels and all ties) stays uncommitted.
    committed_asym = {}
    for idx, counter in labels_by_contact.items():
        label = majority(counter)
        total = sum(counter.values())
        if label is not None:
            assessed[idx] = label
            if total >= 2:
                confirmed[idx] = label
            if total >= 3:
                committed3[idx] = label
        asym = _asym_commit(counter)
        if asym is not None:
            committed_asym[idx] = asym

    def fusion_counts(selected):
        wrong = sum(1 for i, lab in selected.items()
                    if lab != truth[i]["kind"])
        ef = sum(1 for i, lab in selected.items()
                 if truth[i]["kind"] == "Enemy" and lab == "Friendly")
        return wrong, ef

    assessed_wrong, assessed_ef = fusion_counts(assessed)
    confirmed_wrong, confirmed_ef = fusion_counts(confirmed)
    committed3_wrong, committed3_ef = fusion_counts(committed3)
    committed_asym_wrong, committed_asym_ef = fusion_counts(committed_asym)
    committed_asym_friendly = sum(
        1 for lab in committed_asym.values() if lab == "Friendly")

    # Inclusive counterfactual, renamed committed_inclusive_delta per
    # Amendment 1.4: analysis-only, never gated. Fuses direct + hearsay +
    # unverified (never forged) via the shared rule and counts inclusive
    # commits whose outcome differs from direct-only (absent, or a
    # different label). Lenient mapping skips malformed non-voting
    # sightings instead of raising.
    inclusive_labels = collections.defaultdict(collections.Counter)
    for ev in raw_discoveries:
        if _auth_norm(ev) not in FUSIBLE:
            continue
        idx = _lenient_index(ev)
        if idx is not None:
            inclusive_labels[idx][ev["reported_label"]] += 1
    inclusive_asym = {}
    for idx, counter in inclusive_labels.items():
        asym = _asym_commit(counter)
        if asym is not None:
            inclusive_asym[idx] = asym
    committed_inclusive_delta = sum(
        1 for idx, lab in inclusive_asym.items()
        if committed_asym.get(idx) != lab)

    # True P1 (Amendment 1.4): hearsay/unverified sightings vote only for
    # contacts with at least one direct_verified sighting, deduplicated by
    # (contact, claimed_sender, origin_turn) so a relay is never a second
    # vote for the same observation. Fallback when step-2 fields are
    # absent: claimed_sender -> reporter's unit, origin_turn -> event turn.
    # Direct sightings seed the seen-set as (contact, unit, turn), so a
    # relay of an already-voted observation is also deduped. Unhashable
    # sender/origin values fail closed (vote skipped, census kept).
    p1_labels = collections.defaultdict(
        collections.Counter,
        {idx: collections.Counter(cnt)
         for idx, cnt in labels_by_contact.items()})
    seen_obs = set()
    for ev in discoveries:
        idx, _ = contact_of(ev)
        # Bridge-shaped journals (kulira Contract v1) may omit `turn`
        # on direct sightings; fail closed without crashing: seed
        # with origin_turn-or-turn-or-None (None never matches a
        # hearsay origin_turn int, so a relay of a turn-less direct
        # sighting counts once under P1's direct precondition,
        # documented in the cycle-07 amendment trail).
        seen_obs.add((idx, ev.get("claimed_sender", ev.get("unit")),
                      ev.get("origin_turn", ev.get("turn"))))
    for ev in raw_discoveries:
        if _auth_norm(ev) not in ("hearsay_relayed", "unverified"):
            continue
        idx = _lenient_index(ev)
        if idx is None or idx not in labels_by_contact:
            continue
        sender = ev.get("claimed_sender", ev.get("unit"))
        origin = ev.get("origin_turn", ev.get("turn"))
        try:
            key = (idx, sender, origin)
            hash(key)
        except TypeError:
            continue
        if key in seen_obs:
            continue
        seen_obs.add(key)
        p1_labels[idx][ev["reported_label"]] += 1
    committed_p1 = {}
    for idx, counter in p1_labels.items():
        asym = _asym_commit(counter)
        if asym is not None:
            committed_p1[idx] = asym
    committed_p1_wrong, committed_p1_ef = fusion_counts(committed_p1)
    committed_p1_friendly = sum(
        1 for lab in committed_p1.values() if lab == "Friendly")

    by_contact_units = {idx: len(us) for idx, us in found.items()}
    most_dup_idx = (max(by_contact_units,
                        key=lambda idx: (by_contact_units[idx], -idx))
                    if by_contact_units else None)

    covered = set()
    scans = 0
    scans_no_signal = 0
    for ev in scoring:
        if ev["event"] == "scan":
            scans += 1
            scans_no_signal += 1 if ev.get("signals") == 0 else 0
            covered.update(tuple(t) for t in ev.get("footprint", []))

    messages_sent = sum(1 for ev in scoring if ev["event"] == "message_sent")
    checks = [ev for ev in scoring if ev["event"] == "check_assigned"]
    checks_completed = 0
    checks_completed_scan = 0
    checks_positive = 0
    high_checked_completed = 0
    high_checks_positive = 0
    scans_by_unit = collections.defaultdict(list)
    for ev in scoring:
        if ev["event"] == "scan":
            scans_by_unit[ev["unit"]].append(ev)
    contact_by_pos = {}
    for idx, entry in enumerate(truth):
        contact_by_pos.setdefault(tuple(entry["pos"]), idx)
    discoveries_by_unit_contact = collections.defaultdict(list)
    for ev in discoveries:
        idx, _ = contact_of(ev)
        discoveries_by_unit_contact[(ev["unit"], idx)].append(ev)
    for ev in checks:
        dest = tuple(ev["destination"])
        # Turn-less events (bridge-shaped journals) cannot establish
        # ordering, so they never complete a check (fail closed);
        # planner journals always carry turn and are unaffected.
        if ev.get("turn") is not None and any(
                d["unit"] == ev["unit"] and tuple(d["tile"]) == dest
                and d.get("turn") is not None and d["turn"] >= ev["turn"]
                for d in discoveries):
            checks_completed += 1
        completion = next(
            (scan for scan in scans_by_unit[ev["unit"]]
             if ev.get("turn") is not None
             and scan.get("turn") is not None and scan["turn"] > ev["turn"]
             and dest in [tuple(t) for t in scan.get("footprint", [])]),
            None)
        if completion is None:
            continue
        checks_completed_scan += 1
        idx = contact_by_pos.get(dest)
        positive = idx is not None and any(
            d.get("turn") is not None and d["turn"] == completion["turn"]
            for d in discoveries_by_unit_contact[(ev["unit"], idx)])
        is_high = idx is not None and truth[idx].get("priority") == "High"
        if positive:
            checks_positive += 1
        if is_high:
            high_checked_completed += 1
            if positive:
                high_checks_positive += 1
    checks_negative = checks_completed_scan - checks_positive
    high_checks_negative = high_checked_completed - high_checks_positive

    high = [i for i, e in enumerate(truth) if e.get("priority") == "High"]
    high_found = [i for i in high if i in found]
    high_multi = [i for i in high if len(found.get(i, ())) >= 2]
    recall_by_priority = {}
    for priority in sorted({e.get("priority", "Normal") for e in truth}):
        total = sum(1 for e in truth if e.get("priority", "Normal") == priority)
        got = sum(1 for i, e in enumerate(truth)
                  if e.get("priority", "Normal") == priority and i in found)
        recall_by_priority[priority] = _rate(got, total)

    start_energy = {}
    landed = {}
    landed_home_units = set()
    min_energy = {}
    route_by_unit = {}
    reserve_by_unit = {}
    positions = collections.defaultdict(set)
    position_events = {
        "route_assigned", "scan", "return_step", "landed", "check_assigned",
        "message_sent", "message_received", "message_withheld",
    }
    for ev in scoring:
        unit = ev["unit"]
        if ev["event"] in position_events and "tile" in ev:
            positions[unit].add(tuple(ev["tile"]))
        for key in ("energy", "energy_before"):
            if key in ev:
                min_energy[unit] = min(min_energy.get(unit, ev[key]), ev[key])
        if ev["event"] == "route_assigned":
            start_energy.setdefault(unit, ev["energy"])
            route_by_unit.setdefault(
                unit, [tuple(t) for t in ev.get("route", [])])
            if "reserve" in ev:
                reserve_by_unit.setdefault(unit, ev["reserve"])
        elif ev["event"] == "landed":
            landed.setdefault(unit, ev["energy"])
            if tuple(ev["tile"]) == HOME:
                landed_home_units.add(unit)
    spent = {u: start_energy[u] - landed[u]
             for u in landed if u in start_energy}
    reserve_floor_violations = sum(
        1 for u, reserve in reserve_by_unit.items()
        if u in min_energy and min_energy[u] < reserve)
    abandoned_by_unit = {
        u: len({t for t in route if t not in positions[u]})
        for u, route in route_by_unit.items()}
    abandoned_waypoints = sum(abandoned_by_unit.values())
    ground_truth_outcomes = dict(collections.Counter(
        e.get("outcome") for e in truth))

    # Metadata fallback reads scoring (filtered) events only: a forged
    # event must never stamp run/ruleset/source. No scoring event with
    # the field -> null, as today for missing director values.
    def _meta(key):
        if director.get(key):
            return director.get(key)
        return next((ev.get(key) for ev in scoring if ev.get(key)), None)

    return {
        "scorer_version": SCORER_VERSION,
        "run": _meta("run"),
        "ruleset": _meta("ruleset"),
        "source": _meta("source"),
        "units": len(units),
        "contacts_total": len(truth),
        "contacts_found": len(found),
        "recall": _rate(len(found), len(truth)),
        "recall_by_priority": recall_by_priority,
        "high_contacts": len(high),
        "high_found": len(high_found),
        "high_multi_sighted": len(high_multi),
        "high_multi_sighted_rate": _rate(len(high_multi), len(high)),
        "discoveries": len(discoveries),
        "enemy_discoveries": truth_kind_discoveries.get("Enemy", 0),
        "friendly_discoveries": truth_kind_discoveries.get("Friendly", 0),
        "mislabelled": mislabelled,
        "mislabel_rate": _rate(mislabelled, len(discoveries)),
        "mislabelled_enemy_as_friendly": enemy_as_friendly,
        "enemy_as_friendly_per_discovery": _rate(
            enemy_as_friendly, len(discoveries)),
        "enemy_as_friendly_rate_among_enemy": _rate(
            enemy_as_friendly, truth_kind_discoveries.get("Enemy", 0)),
        "mislabelled_friendly_as_enemy": friendly_as_enemy,
        "friendly_as_enemy_rate_among_friendly": _rate(
            friendly_as_enemy, truth_kind_discoveries.get("Friendly", 0)),
        "assessed_contacts": len(assessed),
        "assessed_mislabelled": assessed_wrong,
        "assessed_mislabel_rate": _rate(assessed_wrong, len(assessed)),
        "assessed_enemy_as_friendly": assessed_ef,
        "confirmed_contacts": len(confirmed),
        "confirmed_mislabelled": confirmed_wrong,
        "confirmed_mislabel_rate": _rate(confirmed_wrong, len(confirmed)),
        "confirmed_enemy_as_friendly": confirmed_ef,
        "committed3_contacts": len(committed3),
        "committed3_mislabelled": committed3_wrong,
        "committed3_mislabel_rate": _rate(committed3_wrong, len(committed3)),
        "committed3_enemy_as_friendly": committed3_ef,
        "committed_asym_contacts": len(committed_asym),
        "committed_asym_mislabelled": committed_asym_wrong,
        "committed_asym_mislabel_rate": _rate(
            committed_asym_wrong, len(committed_asym)),
        "committed_asym_enemy_as_friendly": committed_asym_ef,
        "committed_asym_friendly_commits": committed_asym_friendly,
        "duplicate_discoveries": len(discoveries) - len(found),
        "duplicate_discovery_rate": _rate(
            len(discoveries) - len(found), len(discoveries)),
        "max_units_per_contact": by_contact_units[most_dup_idx]
        if most_dup_idx is not None else 0,
        "most_duplicated_tile": list(truth[most_dup_idx]["pos"])
        if most_dup_idx is not None else None,
        "unique_tiles_covered": len(covered),
        "scans": scans,
        "scans_no_signal": scans_no_signal,
        "messages_sent": messages_sent,
        "checks_assigned": len(checks),
        "checks_completed_with_discovery": checks_completed,
        "checks_completed_scan": checks_completed_scan,
        "checks_positive": checks_positive,
        "checks_negative": checks_negative,
        "check_scan_completion_rate": _rate(
            checks_completed_scan, len(checks)),
        "high_checked_completed": high_checked_completed,
        "high_checks_positive": high_checks_positive,
        "high_checks_negative": high_checks_negative,
        "high_check_completion_rate": _rate(
            high_checked_completed, len(high)),
        "units_landed": len(landed),
        "units_landed_home": len(landed_home_units),
        "min_landed_energy": min(landed.values()) if landed else None,
        "min_energy": min(min_energy.values()) if min_energy else None,
        "reserve_floor_violations": reserve_floor_violations,
        "abandoned_waypoints": abandoned_waypoints,
        "units_with_abandoned_waypoints": sum(
            1 for count in abandoned_by_unit.values() if count),
        "total_energy_spent": sum(spent.values()) if spent else None,
        "discoveries_per_energy": round(len(discoveries) / sum(spent.values()), 4)
        if spent and sum(spent.values()) else None,
        # Static director composition, not an assessed journal outcome.
        "ground_truth_outcomes": ground_truth_outcomes,
        "outcomes": ground_truth_outcomes,
        "per_unit_discoveries": {u: per_unit_found.get(u, 0) for u in units},
        # Stage-1 trust metrics (cycle-07 pre-reg + Amendment 1). Journals
        # without auth fields default to direct_verified; attribution and
        # detection latency need step-2 journal fields (claimed_sender/
        # l2_source, treated-unit designation, policy-visible signal
        # event) and stay null ("unmeasured", never 0) until then.
        # reports_by_auth_status is pinned to sighting reports
        # (discoveries) for stage 1. commits_per_energy_unit divides by
        # landed-with-route units' spend only; unlanded spend is invisible
        # to the ratio, so stranding a high-spend unit raises it.
        "reports_by_auth_status": reports_by_auth_status,
        "forged_vote_entries": forged_vote_entries,
        "forged_vote_shaped_attempts": forged_vote_shaped_attempts,
        "committed_inclusive_delta": committed_inclusive_delta,
        "committed_p1_contacts": len(committed_p1),
        "committed_p1_mislabelled": committed_p1_wrong,
        "committed_p1_mislabel_rate": _rate(
            committed_p1_wrong, len(committed_p1)),
        "committed_p1_enemy_as_friendly": committed_p1_ef,
        "committed_p1_friendly_commits": committed_p1_friendly,
        "commits_per_energy_unit": round(
            len(committed_asym) / sum(spent.values()), 4)
        if spent and sum(spent.values()) else None,
        "attribution_accuracy": None,
        "detection_latency_turns": None,
    }


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    scores = score_run(argv[1])
    if "--markdown" in argv:
        print(f"# Scores — run {scores['run']} ({scores['ruleset']}, "
              f"{scores['source']})\n")
        print("| Metric | Value |\n|---|---|")
        for key, value in scores.items():
            if key not in ("run", "ruleset", "source"):
                print(f"| {key} | {value} |")
    else:
        print(json.dumps(scores, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
