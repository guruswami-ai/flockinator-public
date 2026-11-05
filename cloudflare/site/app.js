"use strict";
const out = document.getElementById("bench-out");
function bar(label, cls, rate, counts) {
  const pct = (rate * 100).toFixed(1);
  return `<div class="bar-row"><span>${label}</span><div class="bar ${cls}"><div style="width:${pct}%"></div></div><span>${pct}% <small>${counts}</small></span></div>`;
}
function renderPooled(d) {
  const p = d.pooled;
  out.innerHTML =
    bar("Clear messages", "", p.clear.rate, `${p.clear.recoveries}/${p.clear.tasks}`) +
    bar("Private cues only", "private", p.private.rate, `${p.private.recoveries}/${p.private.tasks}`) +
    bar("Scrambled messages", "scrambled", p.scrambled.rate, `${p.scrambled.recoveries}/${p.scrambled.tasks}`) +
    `<p class="note">Canonical sha256: <code>${d.canonical_sha256.slice(0, 16)}...</code> - precomputed by the Python scientific code, served unchanged.</p>`;
}
function renderSeed(d) {
  const c = d.conditions;
  out.innerHTML = `<p>Seed ${d.seed} (128 team tasks per condition)</p>` +
    bar("Clear messages", "", c.clear.rate, `${c.clear.recoveries}/${c.clear.tasks}`) +
    bar("Private cues only", "private", c.private.rate, `${c.private.recoveries}/${c.private.tasks}`) +
    bar("Scrambled messages", "scrambled", c.scrambled.rate, `${c.scrambled.recoveries}/${c.scrambled.tasks}`);
}
async function load(path, render) {
  out.innerHTML = "<p>Loading...</p>";
  try {
    const r = await fetch(path);
    const d = await r.json();
    if (!r.ok) { out.innerHTML = `<p role="alert">${d.error ? d.error.message : "Request failed"}</p>`; return; }
    render(d);
  } catch (e) { out.innerHTML = `<p role="alert">Benchmark data unavailable offline. Run tools/reproduce from the repository.</p>`; }
}
// Static fallback if Functions are not deployed: read the JSON directly.
async function loadBenchmark(seed) {
  const api = seed === null ? "/api/benchmark" : `/api/benchmark?seed=${seed}`;
  try {
    const r = await fetch(api);
    if (r.ok) { const d = await r.json(); seed === null ? renderPooled(d) : renderSeed(d); return; }
    throw new Error("api");
  } catch (e) {
    const r = await fetch("data/benchmark.json");
    const d = await r.json();
    if (seed === null) { renderPooled(d); return; }
    const row = d.per_seed.find((x) => x.seed === seed);
    if (!row) { out.innerHTML = `<p role="alert">Seed must be 0-15.</p>`; return; }
    renderSeed({ seed, conditions: Object.fromEntries(["clear","scrambled","private"].map(k =>
      [k, { recoveries: row[k+"_recoveries"], tasks: row[k+"_tasks"], rate: row[k+"_recoveries"]/row[k+"_tasks"] }])) });
  }
}
document.getElementById("run-pooled").addEventListener("click", () => loadBenchmark(null));
document.getElementById("run-seed").addEventListener("click", () => {
  const v = Number(document.getElementById("seed").value);
  loadBenchmark(Number.isInteger(v) ? v : -1);
});
loadBenchmark(null);

// Wall replay
const wall = document.getElementById("wall");
const nodes = ["A1","A2","A3","A4","B1","B2","B3","B4","C1","C2","C3","C4","D1","D2","D3","D4"];
wall.innerHTML = nodes.map(n => `<div class="node" id="node-${n}"><strong>${n}</strong><span>idle</span></div>`).join("");
let replay = null, idx = 0, timer = null;
fetch("data/replay.json").then(r => r.json()).then(d => { replay = d; step(); });
function renderContact() {
  const pol = document.getElementById("policy").value;
  const c = replay.contacts[idx];
  nodes.forEach(n => { const el = document.getElementById("node-" + n);
    el.className = "node"; el.querySelector("span").textContent = "idle"; });
  c.reports.forEach(rep => {
    const el = document.getElementById("node-" + rep.node); if (!el) return;
    el.classList.add(rep.forged ? "forged" : (rep.label === "survivor" ? "survivor" : "hazard"));
    el.querySelector("span").textContent = rep.forged ? "FORGED " + rep.modality : rep.modality + ": " + rep.label;
  });
  const decision = c[pol];
  document.getElementById("contact-label").textContent = `Contact ${c.contact + 1}/24 - truth (sealed): ${c.truth}`;
  document.getElementById("verdict").textContent =
    `Policy ${pol}: ${decision === "commit" ? "COMMIT survivor" : "ABSTAIN / no commit"}` +
    (c.contact >= 20 ? " - ir modality is betraying from contact 20" : "");
  if (decision !== "commit") wall.querySelectorAll(".node").forEach(el => el.classList.add("abstain"));
}
function step() { if (!replay) return; renderContact(); idx = (idx + 1) % replay.contacts.length; }
document.getElementById("step").addEventListener("click", step);
document.getElementById("policy").addEventListener("change", () => { idx = Math.max(0, idx - 1); renderContact(); idx = (idx + 1) % replay.contacts.length; });
document.getElementById("play").addEventListener("click", (e) => {
  if (timer) { clearInterval(timer); timer = null; e.target.textContent = "Play replay"; return; }
  e.target.textContent = "Pause";
  timer = setInterval(step, 1100);
});
