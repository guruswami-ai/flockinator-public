#!/usr/bin/env python3
"""Guard: rescue-themed site must never ship KILL/ENGAGE panel animations.

Asserts the site references only audited panel assets, and that the build
script's source segments stay inside the frame-audited safe ranges of
previews/recon-hud/recon-hud.gif (HOLD/SCAN/SEEN/SHARE/CHECK/DOUBT only).
Banned sources: horizon.gif (KILL countdown from frame ~128),
signal-lost.gif, events.gif, close-approach.gif, kill-countdown.gif.
Run: uv run python3 cloudflare/check_panels.py
"""
import pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
site = ROOT / "cloudflare/site"
allowed = {"scan.gif", "share.gif", "check.gif", "doubt.gif", "wall-montage.gif",
           "scan.png", "share.png", "check.png", "doubt.png", "wall-montage.png"}
refs = set()
for f in (site / "index.html", site / "app.js"):
    refs |= set(re.findall(r"panels/([a-z0-9.-]+)", f.read_text()))
refs |= {p.name for p in (site / "panels").iterdir()}
bad = refs - allowed
assert not bad, f"unaudited panel assets referenced: {bad}"
build = (ROOT / "cloudflare/build_panels.py").read_text()
for banned in ("horizon.gif", "signal-lost.gif", "events.gif", "close-approach.gif", "kill-countdown.gif"):
    assert f'"{banned}"' not in (site / "app.js").read_text() and banned not in (site / "index.html").read_text(), banned
segs = {m.group(1): (int(m.group(2)), int(m.group(3))) for m in
        re.finditer(r'"(scan|share|check|doubt)": \((\d+), (\d+)\)', build)}
audited = {"scan": (24, 47), "share": (72, 95), "check": (96, 119), "doubt": (120, 143)}
assert segs.keys() == audited.keys(), segs
for k, (a, b) in segs.items():
    lo, hi = audited[k]
    assert lo <= a and b <= hi, f"{k} segment {a}-{b} outside audited {lo}-{hi}"
print("panel assets OK:", sorted(refs))
