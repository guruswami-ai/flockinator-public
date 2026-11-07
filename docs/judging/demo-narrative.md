# The demonstration in one page

For a researcher or student asking: *can I trust what a group
of small, communicating agents decides - and can I watch it go
wrong?* Flockinator is a bench instrument for that question.
Sixteen ESP32 panels on a wall make a simulated rescue search
visible; behind the wall, every claim below traces to a file
you can re-run.

## What you are looking at

The wall displays a search-and-rescue swarm simulation. Today
the panels render the mission; the scored decisions are made
by host simulation (this is stated, not hidden - see the
[physical execution map](physical-execution-map.md)). The
instrument's value at this stage is the measurement system
around the simulation: pre-registered experiments, frozen
scoring gates, sealed ground truth, and journals that let a
third party reproduce every verdict.

## One flagship result (measured, surprising, falsified once)

**How many aircraft should you commit?** The fleet's original
logic parked 2 of 16 as a reserve - a commander's assumption,
never tested. We tested commitment as an operational question
(a whole day of incidents, not one mission) in four seeded
regimes ([full index](../experiments/operations-commitment-index.md)):

- Benign world: parking 2 costs nothing.
- Binding world: launching all 16 finds *fewer* survivors over
  the day than parking 2 (0.938 vs 0.981) - early
  over-commitment grounds aircraft later incidents need.
- Loss-bearing world: a committed 8 beats both; all-16 loses
  the most aircraft (0.90/day).
- An explorer minority looked promising on dev seeds and then
  **failed its confirmatory run on fresh seeds** (0.644 vs
  0.800) - published as falsified, not quietly dropped.

The trade is real: commitment level is regime-dependent, so
the reserve count should be a tested scenario parameter, not
a constant. That proposal now sits with the planner's owner,
with evidence attached.

## One Meta intervention, measured

A `muse-spark-1.3-contributor` review of our host simulation
twin returned a blunt verdict - "not parity-safe as-is" - with
four concrete defects. The measurable consequence: before the
fix, a device journal truncated to 90 of 100 rows scored
parity **1.0** (a false pass); after it, the same evidence is
correctly reported **UNMEASURED**, and full journals score
exactly 1.000 at 0-20% simulated input loss
([rehearsal](../experiments/canary-host-rehearsal-results.md)).
The full trace - input hash, model, verbatim response,
verification, code change, test outcomes - is in
[Meta contribution bundle 001](../research/meta-contribution-bundle-001.md).

## Reproduce it (about a minute)

```sh
uv run --project tools/kulira-core python -m pytest tools/kulira-core -q   # 200 passed
uv run --project tools/fleet-score python -m pytest tools/fleet-score -q  # 89 passed
python3 tools/reproduce/run.py --out /tmp/repro --verify                  # VERIFY OK
```

## What is not claimed

No on-node inference yet (the canary that tests it is
pre-registered and contract-frozen, not run); no real aircraft;
trust "verified" labels are simulation label segregation, not
cryptography; the submitted competition snapshot and today's
main may differ - this page describes the current public repo.
