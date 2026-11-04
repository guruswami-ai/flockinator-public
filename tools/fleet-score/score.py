#!/usr/bin/env python3
"""Deterministic scorer for flockinator planner journal runs.

Reads one run directory (per-unit ``*.jsonl`` journals plus
``director.json`` ground truth) and computes the balanced scorecard from
docs/design/self-improving-firmware-loop.md. Stdlib only.

Definitions are deliberately plain counts; interpretation lives in cycle
reports, not here. ``contact`` in journal events is a 1-based index into
the director's ``ground_truth`` list (verified against tile positions;
a mismatch raises instead of silently scoring garbage).

Usage: python3 score.py <run-dir> [--markdown]
"""
import collections
import json
import pathlib
import sys

HOME = (7, 11)
SCORER_VERSION = 2


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

    def contact_of(ev):
        contact = ev.get("contact")
        if not isinstance(contact, int) or not 1 <= contact <= len(truth):
            raise ValueError(f"invalid contact index {contact!r} in event {ev!r}")
        idx = contact - 1
        entry = truth[idx]
        if list(entry["pos"]) != list(ev["tile"]):
            raise ValueError(
                f"contact {ev['contact']} tile {ev['tile']} != ground "
                f"truth pos {entry['pos']} (run {ev.get('run')})")
        return idx, entry

    units = sorted({ev["unit"] for ev in events})
    discoveries = [ev for ev in events if ev["event"] == "discovery"]
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

    assessed = {}      # idx -> majority label, >=1 sighting
    confirmed = {}     # idx -> majority label, >=2 sightings
    committed3 = {}    # idx -> majority label, >=3 sightings
    for idx, counter in labels_by_contact.items():
        label = majority(counter)
        if label is not None:
            assessed[idx] = label
            if sum(counter.values()) >= 2:
                confirmed[idx] = label
            if sum(counter.values()) >= 3:
                committed3[idx] = label

    def fusion_counts(selected):
        wrong = sum(1 for i, lab in selected.items()
                    if lab != truth[i]["kind"])
        ef = sum(1 for i, lab in selected.items()
                 if truth[i]["kind"] == "Enemy" and lab == "Friendly")
        return wrong, ef

    assessed_wrong, assessed_ef = fusion_counts(assessed)
    confirmed_wrong, confirmed_ef = fusion_counts(confirmed)
    committed3_wrong, committed3_ef = fusion_counts(committed3)

    by_contact_units = {idx: len(us) for idx, us in found.items()}
    most_dup_idx = (max(by_contact_units,
                        key=lambda idx: (by_contact_units[idx], -idx))
                    if by_contact_units else None)

    covered = set()
    scans = 0
    scans_no_signal = 0
    for ev in events:
        if ev["event"] == "scan":
            scans += 1
            scans_no_signal += 1 if ev.get("signals") == 0 else 0
            covered.update(tuple(t) for t in ev.get("footprint", []))

    messages_sent = sum(1 for ev in events if ev["event"] == "message_sent")
    checks = [ev for ev in events if ev["event"] == "check_assigned"]
    checks_completed = 0
    checks_completed_scan = 0
    checks_positive = 0
    high_checked_completed = 0
    high_checks_positive = 0
    scans_by_unit = collections.defaultdict(list)
    for ev in events:
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
        if any(d["unit"] == ev["unit"] and tuple(d["tile"]) == dest
               and d["turn"] >= ev["turn"] for d in discoveries):
            checks_completed += 1
        completion = next(
            (scan for scan in scans_by_unit[ev["unit"]]
             if scan["turn"] > ev["turn"]
             and dest in [tuple(t) for t in scan.get("footprint", [])]),
            None)
        if completion is None:
            continue
        checks_completed_scan += 1
        idx = contact_by_pos.get(dest)
        positive = idx is not None and any(
            d["turn"] == completion["turn"]
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
    for ev in events:
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

    return {
        "scorer_version": SCORER_VERSION,
        "run": director.get("run") or events[0].get("run"),
        "ruleset": director.get("ruleset") or events[0].get("ruleset"),
        "source": director.get("source") or events[0].get("source"),
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
