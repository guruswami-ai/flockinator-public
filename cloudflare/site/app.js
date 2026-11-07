"use strict";
const out = document.getElementById("bench-out");
function el(tag, text, cls) {
  const n = document.createElement(tag);
  if (text !== undefined) n.textContent = text;
  if (cls) n.className = cls;
  return n;
}
function bar(label, cls, rate, counts) {
  const row = el("div", undefined, "bar-row");
  row.appendChild(el("span", label));
  const barEl = el("div", undefined, "bar " + cls);
  const fill = document.createElement("div");
  fill.style.width = Math.round(rate * 100) + "%";
  barEl.appendChild(fill);
  row.appendChild(barEl);
  const val = el("span", Math.round(rate * 100) + "% ");
  val.appendChild(el("small", counts));
  row.appendChild(val);
  return row;
}
function renderPooled(d) {
  const p = d.pooled;
  out.replaceChildren(
    bar("Clear messages", "", p.clear.rate, `${p.clear.recoveries}/${p.clear.tasks}`),
    bar("Private cues only", "private", p.private.rate, `${p.private.recoveries}/${p.private.tasks}`),
    bar("Scrambled messages", "scrambled", p.scrambled.rate, `${p.scrambled.recoveries}/${p.scrambled.tasks}`),
  );
  const note = el("p", "Canonical sha256: ", "note");
  note.appendChild(el("code", d.canonical_sha256.slice(0, 16) + "..."));
  note.appendChild(document.createTextNode(" - precomputed by the Python scientific code, served unchanged."));
  out.appendChild(note);
}
function renderSeed(d) {
  const c = d.conditions;
  out.replaceChildren(
    el("p", `Seed ${d.seed} (128 team tasks per condition)`),
    bar("Clear messages", "", c.clear.rate, `${c.clear.recoveries}/${c.clear.tasks}`),
    bar("Private cues only", "private", c.private.rate, `${c.private.recoveries}/${c.private.tasks}`),
    bar("Scrambled messages", "scrambled", c.scrambled.rate, `${c.scrambled.recoveries}/${c.scrambled.tasks}`),
  );
}
function showError(msg) {
  const p = el("p", msg);
  p.setAttribute("role", "alert");
  out.replaceChildren(p);
}
// Static fallback if Functions are not deployed: read the JSON directly.
async function loadBenchmark(seed) {
  const api = seed === null ? "/api/benchmark" : `/api/benchmark?seed=${seed}`;
  try {
    const r = await fetch(api);
    if (r.ok) { const d = await r.json(); seed === null ? renderPooled(d) : renderSeed(d); return; }
    throw new Error("api");
  } catch (e) {
    try {
      const r = await fetch("data/benchmark.json");
      const d = await r.json();
      if (seed === null) { renderPooled(d); return; }
      const row = d.per_seed.find((x) => x.seed === seed);
      if (!row) { showError("Seed must be 0-15."); return; }
      renderSeed({ seed, conditions: Object.fromEntries(["clear","scrambled","private"].map(k =>
        [k, { recoveries: row[k+"_recoveries"], tasks: row[k+"_tasks"], rate: row[k+"_recoveries"]/row[k+"_tasks"] }])) });
    } catch (e2) { showError("Benchmark data unavailable offline. Run tools/reproduce from the repository."); }
  }
}
document.getElementById("run-pooled").addEventListener("click", () => loadBenchmark(null));
document.getElementById("run-seed").addEventListener("click", () => {
  const raw = document.getElementById("seed").value.trim();
  const v = raw === "" ? NaN : Number(raw);
  if (!Number.isInteger(v)) { showError("Seed must be an integer 0-15."); return; }
  loadBenchmark(v);
});
loadBenchmark(null);

// Wall replay
const wall = document.getElementById("wall");
const policyLabels = {
  E: "E: verified pool + strict thresholds",
  COMP: "COMP: modality weights + looser thresholds",
};
document.querySelectorAll("#policy option").forEach(option => {
  option.textContent = policyLabels[option.value];
});
const nodes = ["A1","A2","A3","A4","B1","B2","B3","B4","C1","C2","C3","C4","D1","D2","D3","D4"];
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const PANEL = { idle: "scan", survivor: "share", hazard: "check", forged: "doubt" };
function panelSrc(kind) { return "panels/" + PANEL[kind] + (reduceMotion ? ".png" : ".gif"); }
wall.replaceChildren(...nodes.map(n => {
  const d = el("div", undefined, "node"); d.id = "node-" + n;
  const img = document.createElement("img");
  img.src = panelSrc("idle"); img.alt = ""; img.loading = "lazy"; img.className = "panel-gif";
  d.appendChild(img);
  d.appendChild(el("strong", n)); d.appendChild(el("span", "scanning"));
  return d;
}));
if (reduceMotion) document.querySelectorAll("img[data-still]").forEach(i => { i.src = i.dataset.still; });
let replay = null, idx = 0, timer = null, truthRevealed = false;
fetch("data/replay.json").then(r => { if (!r.ok) throw new Error("replay"); return r.json(); })
  .then(d => { if (!d || !Array.isArray(d.contacts)) throw new Error("replay"); replay = d; step(); })
  .catch(() => { document.getElementById("verdict").textContent = "Replay data unavailable."; });
function renderContact() {
  const pol = document.getElementById("policy").value;
  const c = replay.contacts[idx];
  nodes.forEach(n => { const elm = document.getElementById("node-" + n);
    elm.className = "node"; elm.querySelector("span").textContent = "scanning";
    elm.querySelector("img").src = panelSrc("idle"); });
  c.reports.forEach(rep => {
    const elm = document.getElementById("node-" + rep.node); if (!elm) return;
    const kind = rep.forged ? "forged" : (rep.label === "survivor" ? "survivor" : "hazard");
    elm.classList.add(kind);
    elm.querySelector("img").src = panelSrc(kind);
    elm.querySelector("span").textContent = rep.forged ? "FORGED " + rep.modality : rep.modality + ": " + rep.label;
  });
  const decision = c[pol];
  const isLast = c.contact >= replay.contacts.length - 1;
  if (isLast) truthRevealed = true;
  document.getElementById("contact-label").textContent =
    `Contact ${c.contact + 1}/${replay.contacts.length} - ` +
    (truthRevealed ? `truth: ${c.truth}` : "truth: sealed until the final contact");
  document.getElementById("verdict").textContent =
    `Policy ${policyLabels[pol]}: ${decision === "commit" ? "COMMIT survivor" : "ABSTAIN / no commit"}` +
    (c.contact >= 20 ? " - ir modality is betraying from contact 20" : "");
  if (decision !== "commit") wall.querySelectorAll(".node").forEach(elm => elm.classList.add("abstain"));
}
function step() { if (!replay) return; renderContact(); idx = (idx + 1) % replay.contacts.length; }
document.getElementById("step").addEventListener("click", step);
document.getElementById("policy").addEventListener("change", () => { idx = Math.max(0, idx - 1); renderContact(); idx = (idx + 1) % replay.contacts.length; });
document.getElementById("play").addEventListener("click", (e) => {
  if (timer) { clearInterval(timer); timer = null; e.target.textContent = "Play replay"; e.target.setAttribute("aria-pressed", "false"); return; }
  e.target.textContent = "Pause replay"; e.target.setAttribute("aria-pressed", "true");
  timer = setInterval(step, 1100);
});
