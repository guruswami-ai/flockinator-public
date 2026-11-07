# The demonstration in one page

For a researcher or student asking: *can I trust what a group
of small, communicating agents decides - and can I watch it go
wrong?* Flockinator is a bench instrument for that question.
Sixteen ESP32 panels on a wall make a simulated rescue search
visible; behind the wall, the claims below trace to files in
this repository, and the commands at the end re-run the test
suites and the flagship communication benchmark.

## What you are looking at

Watch the [existing physical wall footage](https://flockinator-sim.pages.dev/media.html)
(silent 90-second rescue-retheme demo), or the
[narrated overview](https://www.youtube.com/watch?v=HaYNTBhXbu4).
The wall displays a search-and-rescue swarm simulation. Today
the panels render the mission; the scored decisions are made
by host simulation (this is stated, not hidden - see the
[physical execution map](physical-execution-map.md)). The
instrument's value at this stage is the measurement system
around the simulation: pre-registered experiments, frozen
scoring gates, sealed ground truth, and journals that let a
third party re-check the published verdicts.

That footage shows the physical display, not the benchmark below or
a continuous attack → model review → hardware intervention sequence.

## One host result: message value in a sector-identification task

In [field-signals-v1](../experiments/flagship-communication.md),
team success means at least 3 of 4 agents choose the correct sector.
Across seeds 0–15, each condition has 2,048 held-out team tasks:

| Messages | Successful team tasks | Rate |
|---|---|---|
| Clear peer messages | 1,494 / 2,048 | 72.9% |
| Private cues only (muted) | 1,160 / 2,048 | 56.6% |
| Scrambled peer messages | 688 / 2,048 | 33.6% |

Clear messages help this simulated task; scrambled messages perform worse
than silence. The muted arm receives no peer messages, so information
budgets differ. Tasks within a seed are not independent replicates; inspect
the linked per-seed evidence. This is no measurement of physical rescue
performance or swarm gain at matched information budgets.

## One recorded Meta review and a checked code change

The supervisor recorded a `muse-spark-1.3-contributor` review of our host simulation
twin. It returned a blunt verdict - "not parity-safe as-is" - with
ranked findings. The one with a measurable before and after:
the first comparator scored a synthetic device-format journal truncated to 90
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
The prompt and fan-out script are private; raw API envelopes were not
archived. The public response text and code hashes do not independently
attest the model identity, endpoint or bytes sent to the API.

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
against `tools/reproduce/expected.json`, including the table above. The unit
suites check implementation; they do not rerun a physical mission or
reconstruct the recorded model call. The canary rehearsal remains a separate
host self-check linked above.

## What is not claimed

No on-node inference yet (the canary that tests it is
pre-registered and contract-frozen, not run); no real aircraft;
trust "verified" labels are simulation label segregation, not
cryptography; the submitted competition snapshot and today's
main may differ - this page describes the current public repo.
