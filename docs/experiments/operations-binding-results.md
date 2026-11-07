# Results: binding-regime commitment and reserve (seeds 20-39)

Status: run under
[operations-binding-preregistration.md](operations-binding-preregistration.md)
on the review-corrected simulator. Evidence:
`validation/kulira/operations-binding-001.json`. Simulation only.
Regime: 8 incidents, 160 daylight turns, recharge +4, damage
grounds an aircraft for the rest of the window.

| Strategy | Find rate | Turns to find | Ready end | Ready before inc 2 | Ready before inc 5 | Damaged | Lost | Unattempted |
|---|---|---|---|---|---|---|---|---|---|
| K8 launch 8 fixed | 0.994 | 11.0 | 14.60 | 15.95 | 15.30 | 28 | 0 | 0 |
| K14 park 2 | 0.981 | 6.1 | 14.55 | 15.90 | 15.55 | 29 | 0 | 0 |
| ESC 4 then +8 | 0.981 | 17.0 | 14.75 | 15.95 | 15.45 | 25 | 0 | 2 |
| K8R launch 8 rotate | 0.975 | 10.9 | 14.65 | 15.95 | 15.30 | 27 | 0 | 0 |
| K16 launch all | 0.938 | 5.6 | 14.55 | 15.95 | 15.30 | 29 | 0 | 0 |

Pareto frontier **on the registered axes (find rate vs ready
at end)**: ESC (0.981, 14.75) and K8 (0.994, 14.60). K14 beats
K16 on find rate (0.981 vs 0.938) and readiness before
incident 5 (15.55 vs 15.30), ties it on ready-at-end, damage,
losses and unattempted, trails it slightly on readiness
before incident 2 (15.90 vs 15.95) and on turns-to-find
(6.1 vs 5.6). (Corrected 2026-11-07: an earlier sentence
claimed dominance "on every axis except turns-to-find", which
its own table contradicts on the incident-2 axis.)

## Hypotheses

- **HB1 (regime binds): partially supported.** Damage now grounds
  aircraft for the window, readiness before incident 5 falls to
  ~15.3-15.6, and ESC records 2 unattempted incidents (daylight
  spent on slow early waves). But losses remain **zero under
  every strategy**, so the loss axis still cannot discriminate.
  Battery and forced-landing risk are still too gentle: sorties
  end long before the tactical reserve is threatened.
- **HB2 (reserve protects the operation): falsified as stated,
  with a twist.** K16 matches K14 exactly on lost + unattempted
  (0 and 0), so the reserve buys nothing on the protection axis.
  Yet K14 still beats K16 overall - launching all 16 finds
  *fewer* survivors over the window (0.938 vs 0.981), because
  early over-commitment grounds aircraft that later incidents
  need. The benefit of parking 2 shows up as sustained discovery,
  not as avoided losses.
- **HB3 (rotation preserves readiness): falsified.** K8R equals
  K8 on readiness and losses and finds slightly fewer survivors.
  Rotation remains free but useless in this simulator.
- **HB4 (escalation safest but slowest): falsified.** ESC does
  not have the fewest unattempted incidents - it has the most
  (2), precisely because slow first waves burn daylight. It does
  end with the most ready aircraft and joint-best finds among the
  large strategies, so it is on the frontier, but for readiness
  reasons, not safety.

## What this settles and what it does not

Settled at these parameters: (a) over-commitment can be
operationally *worse* than the current parked-2 strategy across a
multi-incident window, even though it is faster on any single
mission; (b) roster rotation has no measurable value; (c) slow
escalation spends the scarcest operational resource - daylight -
and can leave later incidents unattempted.

Not settled: loss-driven discrimination. With zero losses
everywhere, no strategy can be shown safer. A loss-bearing regime
needs higher mechanical failure, longer far sorties that actually
threaten the tactical reserve, or weather/attrition events - each
a new pre-registration, not a parameter tweak after seeing these
results. Any parked-count change remains a proposal for the
planner owner to test in their own process.
