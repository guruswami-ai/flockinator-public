#!/usr/bin/env python3
"""Cycle-07 step-2 gate runner: T0-T4 x P0-P2 verdicts from scorer outputs.

Inputs: a frozen baseline payload JSON, a candidate run-dir root holding
per-seed run dirs (``seed-<seed>/`` with ``director.json`` + ``*.jsonl``),
and a treatment/policy/matrix config JSON. Scores every candidate seed with
``score.py`` (frozen scorer, never modified here), stamps the candidate
payload with ``scorer_version``, and evaluates the frozen pre-registration
gates G1-G6 as applicable per treatment.

Frozen mapping (pre-registration + supervisor fix review): T0 -> G2, G5, G6;
T1 -> G1; T2 -> G3; T3, T4 -> G4. A treatment config with no applicable
gate is a harness bug and ERRORS (never exits 0 as success).

Treatment ids are bound to the frozen pre-registration definitions
(PRE-REGISTRATION-trust-stage0-stage1.md, lines 62-70), quoted verbatim:
"Treatments (dev seeds 0-19, eligible 16 as frozen):
T0 none (honest baseline rerun for pairing).
T1 outsider forgery: injected events-only discoveries from a non-roster
sender (never enter `reports[k]`).
T2 insider error: one designated unit per seed (unit = seed mod unit_count)
with identify accuracy degraded to 40%.
T3 insider liar: same designated unit flips true-Enemy sightings to Friendly
reports with probability 1.0 (valid key).
T4 patient liar: as T3 but only from turn >= 30."
Only T0-T4 are accepted here. Legacy/extra labels (notably T1R, the
ungated replay emitter, which is explicitly never T2) are REJECTED with an
error, not silently passed or remapped.

Eligibility is a baseline-side frozen property: a seed is eligible iff its
frozen baseline row has contacts_total > 0. Baseline pairing accepts seeded
rows (``per_seed[].seed``) or ordered lists (via the baseline ``seeds``
list, else positional by index); every paired seed asserts candidate
contact totals AND unit counts match the baseline, and any missing or
mismatched seed RAISES. Never silently skipped.

Version rule (Amendment 2.3): the candidate payload MUST carry scorer_version
(it always does: it is scored now) and, when the baseline is stamped, MUST
equal the baseline's. An unstamped candidate is REJECTED outright. A legacy
unstamped baseline is accepted only as the frozen side.

G1 is gated per-seed (max forged_vote_entries == 0), never on an aggregate.
G2/G5 rate is the committed mislabel rate: pooled
committed_<policy>_mislabelled / pooled committed_<policy>_contacts.
Parity attestation requires a non-empty evidence string pointing at the
parity artifact; absent/empty ERRORS. Deterministic: sorted seeds, no wall
clock, no writes outside --out.

Exit codes: 0 PASS (every applicable gate passed), 1 FAIL (any applicable
gate failed), 2 UNMEASURED (no failures, at least one applicable gate
unmeasured, e.g. P2), 3 ERROR (bad config, version/pairing/evidence
violations, missing inputs).

Usage:
  python3 gate_runner.py --baseline baseline-dev.json \
      --runs docs/results/cycle-07/runs/T1 \
      --config docs/results/cycle-07/verdicts/verdicts-cfg-T1-P0.json \
      --out /tmp/verdict-out
"""

import argparse
import json
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from score import SCORER_VERSION, score_run  # noqa: E402

TREATMENTS = ("T0", "T1", "T2", "T3", "T4")
POLICIES = ("P0", "P1", "P2")

EXIT_PASS, EXIT_FAIL, EXIT_UNMEASURED, EXIT_ERROR = 0, 1, 2, 3

# Frozen thresholds (pre-registration, cycle-06 values where referenced).
G2_EF_MAX = 1
G2_RATE_MAX = 0.0750
G3_RECALL_MIN = 0.5141
G4_EF_MAX = 1
G5_CONTACTS_MIN = 30
G6_ENERGY_MEAN_MAX = 214

# Frozen treatment -> gates mapping (pre-registration: G3 gates T2 honest
# error incl. recall floor; G4 gates T3 and T4 liars; G1 gates T1; G2/G5/G6
# gate T0). P2 has no scorer column anywhere: applicable gates report
# UNMEASURED, never 0.
APPLICABLE = {
    "T0": ("G2", "G5", "G6"),
    "T1": ("G1",),
    "T2": ("G3",),
    "T3": ("G4",),
    "T4": ("G4",),
}

# Column families per policy. P0 = direct-only asym commits; P1 = the same
# gate shapes on the P1 (hearsay-fusible) columns. P2 (abstain-on-conflict)
# has no scorer column: reported as unevaluable, never as 0.
COLUMNS = {
    "P0": {"contacts": "committed_asym_contacts",
           "ef": "committed_asym_enemy_as_friendly",
           "mis": "committed_asym_mislabelled"},
    "P1": {"contacts": "committed_p1_contacts",
           "ef": "committed_p1_enemy_as_friendly",
           "mis": "committed_p1_mislabelled"},
    "P2": {"contacts": None, "ef": None, "mis": None},
}


def assert_versions(baseline_payload, candidate_version):
    """Amendment 2.3 version gate. Returns the baseline version (or None)."""
    if candidate_version is None:
        raise ValueError("unstamped candidate payload REJECTED: "
                         "candidate runs must carry scorer_version")
    baseline_version = baseline_payload.get("scorer_version")
    if baseline_version is not None and baseline_version != candidate_version:
        raise ValueError(
            f"scorer-version mismatch: baseline {baseline_version} vs "
            f"candidate {candidate_version}")
    return baseline_version


def pair_baseline(baseline, seeds):
    """Pair config seeds to frozen baseline rows. Never silently skips.

    Seeded rows (``per_seed[].seed``) pair by seed; ordered lists pair by
    the baseline ``seeds`` list, else positionally by config-seed index.
    Missing seeds, length mismatches, and absent ``per_seed`` all RAISE.
    """
    validate_seeds(list(seeds))
    per = baseline.get("per_seed", [])
    if per and all(isinstance(r, dict) and "seed" in r for r in per):
        ids = [r["seed"] for r in per]
        if any(type(i) is not int for i in ids):
            raise ValueError(f"baseline seed ids must be ints, got {ids!r}")
        if len(set(ids)) != len(ids):
            raise ValueError(f"duplicate baseline seed rows: {ids!r}")
        mapping = {r["seed"]: r for r in per}
    elif (isinstance(baseline.get("seeds"), list)
            and len(baseline["seeds"]) == len(per)):
        ids = baseline["seeds"]
        if any(type(i) is not int for i in ids):
            raise ValueError(f"baseline seeds list must be ints, got {ids!r}")
        if len(set(ids)) != len(ids):
            raise ValueError(f"duplicate baseline seeds list: {ids!r}")
        mapping = dict(zip(ids, per))
    elif len(per) == len(seeds):
        mapping = dict(zip(sorted(seeds), per))
    else:
        raise ValueError(
            f"baseline pairing impossible: {len(per)} ordered rows with "
            f"no seed keys/seeds list for {len(seeds)} config seeds")
    missing = [s for s in seeds if s not in mapping]
    if missing:
        raise ValueError(f"config seeds missing from frozen baseline: "
                         f"{missing}")
    return mapping


def validate_evidence(run_dir):
    """Fail-closed evidence checks the frozen scorer does not do.

    Raises ValueError (ERROR verdict) on: exact duplicate discovery
    events, a landed unit with no route_assigned, a route missing
    its reserve field, or non-finite energy values. Legitimate
    distinct observations from one unit are never collapsed.
    """
    import math as _math
    run_dir = pathlib.Path(run_dir)
    events = []
    for path in sorted(run_dir.glob("*.jsonl")):
        for line in path.read_text().splitlines():
            if line.strip():
                events.append(json.loads(line))
    seen, dup = set(), 0
    for ev in events:
        if ev.get("event") == "discovery":
            key = json.dumps(ev, sort_keys=True)
            if key in seen:
                dup += 1
            seen.add(key)
    if dup:
        raise ValueError(f"{run_dir}: {dup} exact duplicate discovery "
                         f"events in evidence")
    routed, landed_units = {}, set()
    for ev in events:
        for k in ("energy", "energy_before"):
            if k in ev and (not isinstance(ev[k], (int, float))
                            or isinstance(ev[k], bool)
                            or not _math.isfinite(ev[k])):
                raise ValueError(f"{run_dir}: non-finite {k} in {ev!r}")
        if ev.get("event") == "route_assigned":
            if "reserve" not in ev:
                raise ValueError(f"{run_dir}: route_assigned without "
                                 f"reserve for {ev.get('unit')!r}")
            routed[ev.get("unit")] = True
        elif ev.get("event") == "landed":
            landed_units.add(ev.get("unit"))
    missing = landed_units - set(routed)
    if missing:
        raise ValueError(f"{run_dir}: landed units with no route: "
                         f"{sorted(missing)}")


def per_seed_metrics(seed, run_dir):
    validate_evidence(run_dir)
    s = score_run(run_dir)
    return {
        "seed": seed,
        "contacts_total": s["contacts_total"],
        "units": s["units"],
        "recall": s["recall"],
        "discoveries": s["discoveries"],
        "forged_vote_entries": s["forged_vote_entries"],
        "forged_vote_shaped_attempts": s["forged_vote_shaped_attempts"],
        "reports_by_auth_status": s["reports_by_auth_status"],
        "committed_asym_contacts": s["committed_asym_contacts"],
        "committed_asym_mislabelled": s["committed_asym_mislabelled"],
        "committed_asym_enemy_as_friendly":
            s["committed_asym_enemy_as_friendly"],
        "committed_p1_contacts": s["committed_p1_contacts"],
        "committed_p1_mislabelled": s["committed_p1_mislabelled"],
        "committed_p1_enemy_as_friendly":
            s["committed_p1_enemy_as_friendly"],
        "total_energy_spent": s["total_energy_spent"],
        "units_landed_home": s["units_landed_home"],
        "reserve_floor_violations": s["reserve_floor_violations"],
    }


def validate_seeds(seeds):
    """Config seeds must be a non-empty list of unique ints.

    bool is rejected explicitly (bool is an int subclass); floats and
    strings that merely look like seeds are config errors, not seeds.
    An empty seed set must never reach the gates: it used to produce
    vacuous PASS verdicts (all([]) is True) with zero rows.
    """
    if not isinstance(seeds, list) or not seeds:
        raise ValueError("config seeds must be a non-empty list")
    bad = [s for s in seeds if type(s) is not int]
    if bad:
        raise ValueError(f"config seeds must be ints, got {bad!r}")
    if len(set(seeds)) != len(seeds):
        raise ValueError(f"config seeds must be unique, got {seeds!r}")


def pooled_mislabel_rate(rows):
    """Frozen rate: pooled committed mislabels / pooled committed contacts.

    Compared UNROUNDED against thresholds; rounding is display-only
    (rounding first admitted 150/1999 = 0.07503... over a 0.0750 cap).
    """
    top = sum(r["mis_col"] for r in rows)
    bottom = sum(r["commit_col"] for r in rows)
    return top / bottom if bottom else None


def mean_eligible_recall(rows):
    vals = [r["recall"] for r in rows if r["eligible"] and r["recall"] is not None]
    return round(statistics.mean(vals), 4) if vals else None


def mean_eligible_energy(rows):
    vals = [r["total_energy_spent"] for r in rows
            if r["eligible"] and r["total_energy_spent"] is not None]
    return round(statistics.mean(vals), 4) if vals else None


def evaluate(treatment, policy, rows, parity):
    """Frozen gates G1-G6 as applicable per treatment (see APPLICABLE).

    Pooled EF is the sum over all seeds; the mislabel rate is pooled
    mislabels / pooled commits; recall and energy are means over eligible
    (baseline-side, contact-bearing) seeds; G5 is the sum of committed
    contacts over all seeds. A treatment with no applicable gate raises
    instead of reporting vacuous success.
    """
    if not rows:
        raise ValueError("no rows to evaluate; refusing vacuous success")
    if treatment not in TREATMENTS:
        raise ValueError(f"unknown treatment {treatment!r}")
    if policy not in POLICIES:
        raise ValueError(f"unknown policy {policy!r}")
    applicable_names = APPLICABLE[treatment]
    if not applicable_names:
        raise ValueError(f"treatment {treatment!r}: no applicable gate; "
                         f"refusing vacuous success")
    cols = COLUMNS[policy]
    for r in rows:
        if cols["contacts"] is None:
            r["commit_col"] = None
            r["ef_col"] = None
            r["mis_col"] = None
        else:
            r["commit_col"] = r[cols["contacts"]]
            r["ef_col"] = r[cols["ef"]]
            r["mis_col"] = r[cols["mis"]]
    unevaluable = cols["contacts"] is None

    def gate(name, passed, value, threshold, detail):
        return {"applicable": name in applicable_names, "pass": passed,
                "value": value, "threshold": threshold, "detail": detail}

    # Treatment engagement: a gate on a treatment that never engaged
    # (no forgery pressure, no commits) is UNMEASURED, never PASS.
    engaged = {
        "T1": sum(r.get("forged_vote_shaped_attempts") or 0 for r in rows) > 0,
        "T3": sum(r["commit_col"] or 0 for r in rows) > 0 if not unevaluable else False,
        "T4": sum(r["commit_col"] or 0 for r in rows) > 0 if not unevaluable else False,
    }
    def _gate_or_unengaged(name, passed, *a):
        if name in ("G1", "G4") and treatment in engaged and not engaged[treatment]:
            return gate(name, None, a[0] if a else None,
                        a[1] if len(a) > 1 else None,
                        f"treatment {treatment} never engaged "
                        f"(no pressure/commits in evidence); UNMEASURED")
        return gate(name, passed, *a)
    g1_max = max(r["forged_vote_entries"] for r in rows) if rows else None
    g1_bad = sorted(r["seed"] for r in rows if r["forged_vote_entries"] != 0)
    gates = {}
    gates["G1"] = _gate_or_unengaged(
        "G1", None if "G1" not in applicable_names else not g1_bad,
        g1_max, 0,
        f"max forged_vote_entries over {len(rows)} seeds; "
        f"failing seeds {g1_bad}")
    ef_total = sum(r["ef_col"] for r in rows
                   if r["ef_col"] is not None) if not unevaluable else None
    mis_rate = pooled_mislabel_rate(rows) if not unevaluable else None
    recall = mean_eligible_recall(rows)
    commit_sum = sum(r["commit_col"] for r in rows) \
        if not unevaluable else None
    energy = mean_eligible_energy(rows)
    energy_unmeasured = any(
        r["eligible"] and (r["total_energy_spent"] is None
                           or r["total_energy_spent"] == 0)
        for r in rows)
    all_home = all(r["units_landed_home"] == r["units"] for r in rows)
    no_viol = all(r["reserve_floor_violations"] == 0 for r in rows)

    if unevaluable:
        reason = "P2 abstain-on-conflict has no scorer v4 column (unmeasured)"
        for name in ("G2", "G3", "G4", "G5", "G6"):
            gates[name] = gate(name, None, None, None, reason)
    else:
        gates["G2"] = gate(
            "G2", None if "G2" not in applicable_names
            else (ef_total <= G2_EF_MAX and mis_rate is not None
                  and mis_rate <= G2_RATE_MAX),
            {"pooled_ef": ef_total, "committed_mislabel_rate": mis_rate},
            {"ef": G2_EF_MAX, "rate": G2_RATE_MAX},
            "pooled EF total and pooled committed-mislabel / pooled commits")
        gates["G3"] = gate(
            "G3", None if "G3" not in applicable_names
            else (ef_total <= G2_EF_MAX and (recall or 0) >= G3_RECALL_MIN),
            {"pooled_ef": ef_total, "mean_recall": recall},
            {"ef": G2_EF_MAX, "recall": G3_RECALL_MIN},
            "honest-error gate: EF no worse than cycle-06, recall floor")
        gates["G4"] = _gate_or_unengaged(
            "G4", None if "G4" not in applicable_names
            else ef_total <= G4_EF_MAX,
            {"pooled_ef": ef_total}, {"ef": G4_EF_MAX},
            "liar gate: no new dangerous commits beyond frozen locus")
        gates["G5"] = gate(
            "G5", None if "G5" not in applicable_names
            else commit_sum >= G5_CONTACTS_MIN,
            {"pooled_contacts": commit_sum}, {"contacts": G5_CONTACTS_MIN},
            "pooled committed contacts (yield floor)")
        g6_detail = (f"mean eligible energy {energy}, all_home {all_home}, "
                     f"no_reserve_violations {no_viol}, parity {parity}")
        gates["G6"] = gate(
            "G6", None if "G6" not in applicable_names or energy_unmeasured
            else (energy is not None and energy <= G6_ENERGY_MEAN_MAX
                  and all_home and no_viol
                  and isinstance(parity, dict)
                  and parity.get("result") == "pass"
                  and isinstance(parity.get("evidence"), str)
                  and bool(parity["evidence"].strip())),
            {"mean_energy": energy, "all_home": all_home,
             "no_reserve_violations": no_viol, "parity": parity},
            {"energy": G6_ENERGY_MEAN_MAX, "parity": "pass"},
            g6_detail)
    info = {
        "max_forged_vote_entries": g1_max,
        "failing_forgery_seeds": g1_bad,
        "pooled_ef": ef_total,
        "committed_mislabel_rate": mis_rate,
        "mean_eligible_recall": recall,
        "pooled_committed_contacts": commit_sum,
        "mean_eligible_energy": energy,
        "all_units_landed_home": all_home,
        "no_reserve_violations": no_viol,
    }
    applicable = [g for g in gates.values() if g["applicable"]]
    if not applicable:
        raise ValueError(f"treatment {treatment!r}: no applicable gate; "
                         f"refusing vacuous success")
    passes = [g["pass"] for g in applicable]
    if any(p is False for p in passes):
        all_pass = False
    elif any(p is None for p in passes):
        all_pass = None
    else:
        all_pass = True
    return {"gates": gates, "info": info, "all_applicable_pass": all_pass}


def verdict_exit(verdict):
    """Three-valued exit: False -> FAIL, None -> UNMEASURED, True -> PASS."""
    result = verdict["all_applicable_pass"]
    if result is False:
        return EXIT_FAIL
    if result is None:
        return EXIT_UNMEASURED
    return EXIT_PASS


def render_table(treatment, policy, verdict):
    lines = [f"| Gate | Applies | Value | Threshold | Result |",
             f"|---|---|---|---|---|"]
    for name in ("G1", "G2", "G3", "G4", "G5", "G6"):
        g = verdict["gates"][name]
        if not g["applicable"]:
            result = "N/A"
        elif g["pass"] is None:
            result = "UNMEASURED"
        else:
            result = "PASS" if g["pass"] else "FAIL"
        lines.append(f"| {name} ({treatment}/{policy}) | "
                     f"{'yes' if g['applicable'] else 'no'} | "
                     f"{json.dumps(g['value'], sort_keys=True)} | "
                     f"{json.dumps(g['threshold'], sort_keys=True)} | "
                     f"{result} |")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--runs", required=True,
                    help="candidate run-dir root with seed-<seed>/ subdirs")
    ap.add_argument("--config", required=True,
                    help='JSON: {"treatment","policy","seeds",'
                         '"parity": {"result","evidence"}}')
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    # Any run attempt invalidates a previous verdict in --out, so a
    # failed run can never leave a stale PASS behind.
    stale = pathlib.Path(args.out) / "verdict.json"
    if stale.exists():
        stale.unlink()
    baseline = json.loads(pathlib.Path(args.baseline).read_text())
    config = json.loads(pathlib.Path(args.config).read_text())
    validate_seeds(config.get("seeds"))
    treatment, policy, seeds = (config["treatment"], config["policy"],
                               sorted(config["seeds"]))
    parity = config.get("parity")
    if treatment not in TREATMENTS or policy not in POLICIES:
        raise ValueError("config treatment/policy not in T0-T4 / P0-P2")
    if (not isinstance(parity, dict) or not parity.get("result")
            or not isinstance(parity.get("evidence"), str)
            or not parity["evidence"].strip()):
        raise ValueError(
            "parity attestation required: config.parity must carry result "
            "and a non-empty evidence string pointing at the parity artifact")
    baseline_map = pair_baseline(baseline, seeds)
    runs_root = pathlib.Path(args.runs)
    rows = []
    for seed in seeds:
        d = runs_root / f"seed-{seed}"
        if not d.is_dir():
            raise FileNotFoundError(f"missing candidate run dir {d}")
        row = per_seed_metrics(seed, d)
        base = baseline_map[seed]
        if base.get("contacts_total") != row["contacts_total"]:
            raise ValueError(f"seed {seed}: contact totals differ "
                             f"(baseline {base.get('contacts_total')} vs "
                             f"candidate {row['contacts_total']})")
        if base.get("units") != row["units"]:
            raise ValueError(f"seed {seed}: unit counts differ "
                             f"(baseline {base.get('units')} vs "
                             f"candidate {row['units']})")
        # Eligibility is frozen baseline-side, never candidate-derived.
        row["eligible"] = (base.get("contacts_total") or 0) > 0
        rows.append(row)
    candidate_version = SCORER_VERSION
    baseline_version = assert_versions(baseline, candidate_version)
    verdict = evaluate(treatment, policy, rows, parity)
    payload = {
        "treatment": treatment,
        "policy": policy,
        "seeds": seeds,
        "scorer_version": candidate_version,
        "baseline_version": baseline_version,
        "baseline_label": baseline.get("label"),
        "parity_evidence": parity["evidence"],
        "per_seed": rows,
        **verdict,
    }
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "verdict.json").write_text(json.dumps(payload, indent=1,
                                                  sort_keys=True) + "\n")
    table = render_table(treatment, policy, verdict)
    print(table)
    print(f"verdict: {out / 'verdict.json'}")
    print(f"all_applicable_pass: {verdict['all_applicable_pass']}")
    return verdict_exit(verdict)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(f"gate_runner error: {exc}", file=sys.stderr)
        raise SystemExit(EXIT_ERROR)
