# Pre-registration (future, gated): live sensor-mode experiments

Status: **registered intent, not runnable yet.** These require
the live shared-world simulation (nodes deciding locally) and
therefore sit *after* the panel-policy canary. Adapted from a
contributor draft in `docs/research/contributor-notes/` with
seed ranges corrected to this programme's allocation. No run is
authorised by this document alone; each experiment needs its
own lock (parameters, firmware build, canary gates) before
execution. Simulation world, real node execution when run.

Modes per node per search: Day camera, thermal White-Hot,
thermal Black-Hot, Night, IR (already rendered by the panels).

## SM1 Diversity vs uniformity (easiest, first)

- Question: does fixed mode diversity find the survivor faster
  than a uniform mode?
- Manipulation: Uniform (all Day) vs Diverse (4/4/4/4 across
  modes), no switching inside a search, same seeds paired.
- Primary metric: mean turns-to-find; secondary find rate.
- Falsified if Diverse is not faster *and* not higher on find
  rate.
- Seeds 120-139.

## SM2 Switching cost

- Question: does a mode-switch blackout (10 ticks) reduce
  thrashing without harming find time?
- Manipulation: free switching vs costly switching.
- Primary metrics: switches per search, turns-to-find.
- Falsified if Costly does not reduce switches, or is >20%
  slower to find.
- Seeds 140-159.

## SM3 Trust after degradation (hardest)

- Question: do nodes abandon a sensor mode after the director
  degrades it (detection 95% -> 30%, false alarms up), using
  only local observations plus one broadcast notice?
- Primary metrics: fraction leaving the degraded mode, find
  rate vs no-degradation control.
- Falsified if <50% leave, or find rate equals control despite
  leaving (switching is theatre).
- Seeds 160-179.

## Gate

SM1 may be locked only after the canary passes its parity and
journal-completeness gates. SM3 additionally requires the
degradation broadcast to ride the EVENT frame of the SIM wire
format (`kulira_core/simwire.py` reference implementation).
Planner/firmware changes remain Drishdi-owned.
