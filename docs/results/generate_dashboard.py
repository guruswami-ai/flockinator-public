#!/usr/bin/env python3
"""Generate the Flockinator training-session results dashboard.

Reads results-data.json (frozen, lane-reviewed cycle aggregates) from this
directory and writes a self-contained index.html with inline SVG charts.
Stdlib only. Usage: uv run --no-project docs/results/generate_dashboard.py
"""
import json, pathlib, html as H
HERE = pathlib.Path(__file__).resolve().parent
D = json.loads((HERE / "results-data.json").read_text())
C = [c for c in D["candidates"] if c["sighted_recall"] is not None]
V = D.get("next")
GATE = D["gates"]["sighted_recall_min"]
AMBER, RED, TEAL, INK = "#e0a526", "#c84b31", "#2e8b7a", "#9fb4c8"
def esc(s): return H.escape(str(s))

def bars(rows, vmax, fmt="{:.2f}", gate=None, unit=""):
    w, bh, gap, lab, pad = 860, 34, 14, 255, 90
    h = len(rows) * (bh + gap) + 12
    out = [f'<svg viewBox="0 0 {w} {h}" role="img">']
    for i, (name, val, col) in enumerate(rows):
        y = 6 + i * (bh + gap)
        bw = max(2, (val / vmax) * (w - lab - pad))
        out.append(f'<text x="0" y="{y+bh-11}" class="sl">{esc(name)}</text>')
        out.append(f'<rect x="{lab}" y="{y}" width="{bw:.0f}" height="{bh}" fill="{col}"/>')
        out.append(f'<text x="{lab+bw+8:.0f}" y="{y+bh-11}" class="sv">{fmt.format(val)}{unit}</text>')
    if gate:
        gx = lab + (gate / vmax) * (w - lab - pad)
        out.append(f'<line x1="{gx:.0f}" y1="0" x2="{gx:.0f}" y2="{h}" stroke="{RED}" stroke-width="2" stroke-dasharray="5 4"/>')
        out.append(f'<text x="{gx+6:.0f}" y="12" class="sg">gate {gate}</text>')
    out.append("</svg>")
    return "".join(out)

recall = bars([(c["name"], c["sighted_recall"], TEAL if c["verdict"] == "production" else AMBER) for c in C], 0.75, "{:.4f}", GATE)
committed = bars([(c["name"], c["committed"], INK) for c in C], 60, "{:.0f}")
ef = bars([(c["name"], c["committed_ef"], RED) for c in C], 3, "{:.0f}")
energy = bars([(c["name"], c["energy"], INK) for c in C], 230, "{:.1f}")

dots = []
pts = [p for p in D["per_seed_recall_delta_sector"] if p["eligible"]]
w, h, mid = 860, 190, 95
dots.append(f'<svg viewBox="0 0 {w} {h}" role="img"><line x1="40" y1="{mid}" x2="{w-10}" y2="{mid}" stroke="#44515f"/>')
for i, p in enumerate(pts):
    x = 50 + i * ((w - 70) / max(1, len(pts) - 1))
    y = mid - (p["delta"] or 0) * 80
    col = TEAL if (p["delta"] or 0) >= 0 else RED
    dots.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="6" fill="{col}"><title>seed {p["seed"]}: {p["delta"]:+.4f}</title></circle>')
    dots.append(f'<text x="{x-4:.0f}" y="{h-6}" class="sg">{p["seed"]}</text>')
dots.append(f'<text x="40" y="16" class="sg">per-seed sighted-recall delta, sector v1 minus baseline (eligible seeds)</text></svg>')
dots = "".join(dots)

cards = "".join(
    f'<div class="card"><div class="ch"><b>{esc(c["name"])}</b><span class="tag {c["verdict"]}">{c["verdict"].upper()}</span></div>'
    f'<div class="cm">recall {c["sighted_recall"]:.4f} · committed {c["committed"]} · wrong {c["committed_wrong"]} · '
    f'<b class="{"bad" if c["committed_ef"] else "ok"}">Enemy→Friendly {c["committed_ef"]}</b> · energy {c["energy"]:.1f}</div>'
    f'<p>{esc(c["note"])}</p><div class="cm">{esc(c["committed_basis"])} · {esc(c["cycle"])}</div></div>'
    for c in C)
if V:
    cards += (f'<div class="card next"><div class="ch"><b>{esc(V["name"])}</b><span class="tag pre">OPEN PROBLEM</span></div>'
              f'<p>{esc(V["note"])}</p><div class="cm">{esc(V["basis"])}</div></div>')

rows = "".join(
    f'<tr><td>≥{r["min_sightings"]}</td>' + "".join(
        f'<td>{v[0]} / {v[1]} / <b class="{"bad" if v[2] else "ok"}">{v[2]}</b></td>'
        for v in (r["baseline"], r["sector_v1"], r["sector_confirm_v2"])) + "</tr>"
    for r in D["threshold_tradeoff"]["rows"])

fw = "".join(
    f'<h3>{esc(g["component"])}</h3><table>' + "".join(f'<tr><td class="ver">{esc(v)}</td><td>{esc(d)}</td></tr>' for v, d in g["versions"]) + "</table>"
    for g in D["firmware_evolution"])
flow = "".join(f"<li>{esc(s)}</li>" for s in D["decision_flow"])

html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Flockinator — training-session results</title>
<meta name="description" content="Flockinator planner simulation results, four rejected candidates, hardware field observations and reproducible scorer fixtures.">
<style>
:root{{--bg:#14181d;--panel:#1c222a;--line:#39434f;--tx:#e8e4da;--dim:#a9b2bc;--amber:#e0a526;--red:#e0674f;--teal:#3fae97}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--tx);font:16px/1.55 Georgia,'Times New Roman',serif}}
main{{max-width:920px;margin:0 auto;padding:32px 20px 64px}}
h1{{font-size:34px;line-height:1.15;margin:0 0 6px}}h2{{font-size:22px;margin:38px 0 10px;border-top:2px solid var(--amber);padding-top:14px}}
h3{{font-size:17px;margin:20px 0 6px}}p{{margin:8px 0}}.lede{{font-size:18px;color:var(--dim)}}
svg{{width:100%;height:auto;background:var(--panel);border:1px solid var(--line)}}
.sl{{fill:var(--tx);font:12px ui-monospace,Menlo,monospace}}.sv{{fill:var(--tx);font:14px ui-monospace,Menlo,monospace}}
.sg{{fill:var(--dim);font:11px ui-monospace,Menlo,monospace}}
.card{{background:var(--panel);border:1px solid var(--line);padding:14px 16px;margin:10px 0}}
.card.next{{border-style:dashed}}.ch{{display:flex;justify-content:space-between;gap:10px;align-items:baseline}}
.cm{{font:13px ui-monospace,Menlo,monospace;color:var(--dim);margin:4px 0}}
.tag{{font:11px ui-monospace,Menlo,monospace;padding:2px 8px;border:1px solid var(--line)}}
.tag.production{{color:var(--teal)}}.tag.rejected{{color:var(--red)}}.tag.pre{{color:var(--amber)}}
.bad{{color:var(--red)}}.ok{{color:var(--teal)}}
table{{border-collapse:collapse;width:100%;font:14px ui-monospace,Menlo,monospace;margin:8px 0}}
th,td{{border:1px solid var(--line);padding:6px 9px;text-align:left}}th{{color:var(--amber)}}
td.ver{{white-space:nowrap;color:var(--amber)}}
ol.flow{{counter-reset:step;list-style:none;padding:0}}
ol.flow li{{counter-increment:step;background:var(--panel);border:1px solid var(--line);padding:10px 14px 10px 52px;margin:6px 0;position:relative}}
ol.flow li::before{{content:counter(step);position:absolute;left:14px;top:8px;font:20px ui-monospace,Menlo,monospace;color:var(--amber)}}
pre{{background:#0d1013;border:1px solid var(--line);padding:12px 14px;overflow-x:auto;font:13px/1.5 ui-monospace,Menlo,monospace}}
code{{font:13px ui-monospace,Menlo,monospace;background:#0d1013;padding:1px 5px}}a{{color:var(--amber)}}
.finding{{background:#241d10;border:1px solid var(--amber);padding:14px 16px;margin:16px 0}}
.dim{{color:var(--dim);font-size:14px}}
@media (prefers-reduced-motion: reduce){{*{{animation:none;transition:none}}}}
</style></head><body><main>
<h1>Evaluating decisions in a simulated swarm</h1>
<p class="lede">Flockinator's planner scorecard records a frozen baseline and
<span style="color:var(--red)">four rejected candidates</span>. These are simulation
replay results evaluated against pre-registered promotion gates.</p>
<p>This dashboard is generated from <a href="results-data.json">published aggregate
reports</a>. Bundled synthetic journals reproduce scorer fixtures. Reproducing all
aggregate results requires the corresponding complete run sets. The
<a href="README.md">results record</a> explains provenance and hardware field observations.</p>

<div class="finding">Search coverage improved, while all four tested candidates
failed the full promotion criteria. These results support rejecting those candidates
under the recorded conditions. Graded sensing and explicit abstention are proposed
next experiments.</div>
<p class="dim">Historical Friendly/Enemy labels are retained for traceability.
The current public scenario uses a search-and-rescue narrative.</p>

<h2>1 · Sighted recall — did the swarm find the contacts?</h2>
{recall}
{dots}
<p class="dim">Dev set: 20 seeded scenarios, 16 eligible under the frozen baseline-energy rule.
Holdout (sealed seeds 100–109) baseline recall on eligible seeds: 0.2055. Sealed means
sealed: it was never run for a rejected candidate.</p>

<h2>2 · Committed decisions — and the one error that matters</h2>
<p>A <i>committed</i> label is what the commander would act on. Committing <b>Enemy as
Friendly</b> is the dangerous direction, so its gate is absolute: <b>zero</b>.</p>
<h3>Committed contacts (pooled)</h3>{committed}
<h3>Dangerous commits — Enemy→Friendly (gate = 0)</h3>{ef}
{cards}
<table><tr><th>Min. sightings to commit</th><th>Baseline</th><th>Sector v1</th><th>Sector + confirm v2</th></tr>{rows}</table>
<p class="dim">Cells are committed / mislabelled / Enemy→Friendly on identical journals.
Stricter rules buy safety with yield — and at ≥3 a dangerous commit still slips through
under v2 sighting patterns.</p>

<h2>3 · Energy — what did certainty cost?</h2>
{energy}
<p class="dim">Mean total energy per eligible seed. Confirmation is not free: completed check
scans rose {D["checks"]["baseline_check_scans"]} → {D["checks"]["sector_check_scans"]} →
{D["checks"]["v2_check_scans"]} → {D["checks"]["v3_check_scans"]} across generations. Every unit
still landed home with zero reserve-floor violations in every run.</p>

<h2>4 · How a contact becomes a decision</h2>
<ol class="flow">{flow}</ol>

<h2>5 · Firmware evolution</h2>
{fw}

<h2>6 · Reproduce it</h2>
<p>The scorer is deterministic, stdlib-only Python. The bundled synthetic fixtures
include baseline seeds 0 and 10 with eight units and a sixteen-unit planner capture.
Run these commands from the repository root.</p>
<pre>uv run --project tools/fleet-score python tools/fleet-score/score.py docs/results/sample-runs/baseline-seed-10
uv run --project tools/fleet-score python tools/fleet-score/score.py docs/results/sample-runs/cycle-00-planner-capture
uv run --project tools/fleet-score python -m pytest tools/fleet-score -q
uv run --project tools/fleet-score python docs/results/generate_dashboard.py</pre>
<p>Full protocol — pre-registration, eligible-seed rules, sealed holdout, gate definitions,
restore-on-failure discipline — is in the <a href="README.md">results README</a>. Extend it:
write your pre-registration first, then beat <b>recall ≥ 0.5141 with Enemy→Friendly = 0</b>.</p>
<p class="dim">Guardrails: gates frozen before candidates ran; identification rolls are never
used as commit confidence (in this simulator the roll determines correctness — using it
would be oracle leakage, not sensing); planner replay is simulation evidence, never
claimed as on-node inference. On-device measurement (controller health API, fleet sweep,
node SD journal copies) records infrastructure behaviour. Evaluating learning
on physical nodes requires attributable node decisions and matched experiment runs.</p>
</main></body></html>
"""
(HERE / "index.html").write_text(html)
print("wrote", HERE / "index.html", len(html), "bytes")
