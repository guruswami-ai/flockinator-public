# The demonstration in one page

For a researcher or student asking: *can I trust what a group
of small, communicating agents decides - and can I watch it go
wrong?* Flockinator is a bench instrument for that question.
Sixteen ESP32 panels on a wall make a simulated rescue search
visible; behind the wall, the claims below trace to files in
this repository, and the commands at the end re-run the test
suites and the flagship communication benchmark.

## What you are looking at

The wall displays a search-and-rescue swarm simulation. Today
the panels render the mission; the scored decisions are made
by host simulation (this is stated, not hidden - see the
[physical execution map](physical-execution-map.md)). The
instrument's value at this stage is the measurement system
around the simulation: pre-registered experiments, frozen
scoring gates, sealed ground truth, and journals that let a
third party re-check the published verdicts.

## One flagship result (measured, surprising, falsified once)

**How many aircraft should you commit?** The fleet's original
logic parked 2 of 16 as a reserve - a commander's assumption,
never tested. We tested commitment as an operational question
(a whole day of incidents, not one mission) in four seeded
regimes ([full index](../experiments/operations-commitment-index.md)):

- Benign world (seeds 0-19): parking 2 costs nothing
  measurable.
- Binding world (seeds 20-39): launching all 16 finds *fewer*
  survivors over the day than parking 2 (find rate 0.938 vs
  0.981) - early over-commitment grounds aircraft later
  incidents need.
- Loss-bearing world (seeds 40-59): a committed 8 beats both
  on finds; all-16 loses the most aircraft (0.90 per daylight
  window).
- An explorer minority looked promising on dev seeds and then
  **failed its confirmatory run on fresh seeds** (seeds
  100-119, find rate 0.644 vs 0.800) - published as falsified,
  not quietly dropped.

The trade is real: commitment level is regime-dependent, so
the reserve count should be a tested scenario parameter, not
a constant. That proposal now sits with the planner's owner,
with evidence attached.

## One Meta intervention, measured

A `muse-spark-1.3-contributor` review of our host simulation
twin returned a blunt verdict - "not parity-safe as-is" - with
ranked findings. The one with a measurable before and after:
the first comparator scored a device journal truncated to 90
of 100 rows as parity **1.0** (a false pass). The fix made in
response (PR #122) returns `parity: None` with
`length_mismatch: true` for that case, and a regression test
pins it (`tools/kulira-core/test_twin.py`). The comparator
function reports those fields; it does not emit a verdict
label such as UNMEASURED - that word belongs to the fleet-score
gate runner.

Two later changes are separate from that review: PR #126 made
agreement per-row over identity, hash and decision after the
2026-11-07 reassessment found the earlier formula overstated
it, and PR #137 added the contract v1.1 missing-input
semantics. Under v1.1 the
[host rehearsal](../experiments/canary-host-rehearsal-results.md)
scores full host-generated journals at exactly 1.000 parity
with 0-20% simulated input loss - a comparator self-check, not
device execution.

The inspectable artifacts - the verbatim response note with its
SHA-256, the git blob and SHA-256 of the recorded source revision
(its link to the model identity and the request input rests on
the supervisor's record, as the bundle states), the PR diffs and
the suite outcomes at each merge - are listed with verifier
commands in
[Meta contribution bundle 001](../research/meta-contribution-bundle-001.md).
The prompt, the fan-out script and the raw API envelope are not
public; the bundle records that limit.

## Reproduce it (about a minute)

```sh
uv run --project tools/kulira-core python -m pytest tools/kulira-core -q   # kulira-core unit tests
uv run --project tools/fleet-score python -m pytest tools/fleet-score -q   # fleet-score unit tests
uv run python tools/reproduce/run.py --verify     # flagship field-signals benchmark vs expected.json
```

The first two lines run the unit suites; pass counts are
commit-specific, so read them from the run rather than from this
page. The third regenerates the field-signals-v1 communication
benchmark (seeds 0-15) and compares its scientific content
against `tools/reproduce/expected.json`. None of the three rebuilds the
commitment, explorer or canary tables above; those come from the
validation JSON files linked from each results page.

## What is not claimed

No on-node inference yet (the canary that tests it is
pre-registered and contract-frozen, not run); no real aircraft;
trust "verified" labels are simulation label segregation, not
cryptography; the submitted competition snapshot and today's
main may differ - this page describes the current public repo.
