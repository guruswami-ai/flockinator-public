"""Wall report: the human lens for a wall-observer session.

Turns timestamped frames into what a human can actually compare:
per-cell (4x4) visual state per mission phase, first-vs-last
heatmaps, a per-cell change chart, and headline statistics. This is
the comparison view for beginning / training / end mission states:
statistical improvement in the journals is necessary, but the wall
must also *look* different, cell by cell.

Pure stdlib. Image decoding is injected (`loader(path) -> pixels`)
so tests need no imaging library; the CLI supplies a PIL loader when
Pillow is available and says how to get it when it is not.

Measured rig geometry (Pixel 9a central mount, 2026-11-06): the
camera sees the panels from behind, so frames are mirror-flipped
before sampling, and the wall quad in frame fractions is
DEFAULT_CORNERS. Rows top->bottom are D,C,B,A; columns 1..4.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .log import verify_log
from .wall_observer import file_sha256

DEFAULT_CORNERS = ((0.045, 0.03), (0.99, 0.04), (0.835, 0.995), (0.18, 0.985))
ROW_LABELS = ("D", "C", "B", "A")
COL_LABELS = ("1", "2", "3", "4")


def cell_name(r: int, c: int) -> str:
    return f"{ROW_LABELS[r]}{COL_LABELS[c]}"


def _bilinear(u: float, v: float, corners) -> tuple[float, float]:
    (tl, tr, br, bl) = corners
    top = (tl[0] + (tr[0] - tl[0]) * u, tl[1] + (tr[1] - tl[1]) * u)
    bot = (bl[0] + (br[0] - bl[0]) * u, bl[1] + (br[1] - bl[1]) * u)
    return (top[0] + (bot[0] - top[0]) * v, top[1] + (bot[1] - top[1]) * v)


def sample_cells(get_px, w: int, h: int, corners=DEFAULT_CORNERS,
                 samples: int = 8) -> list[list[tuple[float, float, float]]]:
    """Mean RGB per cell. get_px(x, y) -> (r, g, b) at pixel coords."""
    grid = []
    for r in range(4):
        row = []
        for c in range(4):
            acc = [0.0, 0.0, 0.0]
            n = 0
            for i in range(samples):
                for j in range(samples):
                    u = (c + (j + 0.5) / samples) / 4
                    v = (r + (i + 0.5) / samples) / 4
                    fx, fy = _bilinear(u, v, corners)
                    px = get_px(min(w - 1, max(0, int(fx * w))),
                                min(h - 1, max(0, int(fy * h))))
                    for k in range(3):
                        acc[k] += px[k]
                    n += 1
            row.append(tuple(a / n for a in acc))
        grid.append(row)
    return grid


def _avg_grids(grids):
    return [[tuple(sum(g[r][c][k] for g in grids) / len(grids)
                   for k in range(3)) for c in range(4)] for r in range(4)]


def _brightness(cell) -> float:
    return 0.2126 * cell[0] + 0.7152 * cell[1] + 0.0722 * cell[2]


def compare_grids(a, b) -> dict:
    """Per-cell change between two phase grids (a=first, b=last)."""
    cells = []
    for r in range(4):
        for c in range(4):
            d = math.sqrt(sum((b[r][c][k] - a[r][c][k]) ** 2 for k in range(3)))
            cells.append({"cell": cell_name(r, c), "row": r, "col": c,
                          "rgb_delta": round(d, 2),
                          "brightness_delta": round(
                              _brightness(b[r][c]) - _brightness(a[r][c]), 2)})
    deltas = [c["rgb_delta"] for c in cells]
    return {"cells": cells,
            "mean_rgb_delta": round(sum(deltas) / len(deltas), 2),
            "max_rgb_delta": round(max(deltas), 2),
            "cells_changed_over_25": sum(1 for d in deltas if d > 25)}


def load_session_phases(session_dir, loader, flip: bool = True) -> dict:
    """{phase: {grid, frames:[...]}} in manifest order."""
    d = Path(session_dir)
    entries = verify_log(d / "manifest.jsonl")
    phases: dict[str, list] = {}
    order: list[str] = []
    for e in entries:
        if e["kind"] != "frame" or e["payload"].get("kind_media") != "still":
            continue
        p = e["payload"]
        path = d / p["file"]
        if file_sha256(path) != p["sha256"]:
            raise ValueError(f"sha256 mismatch {path}")
        pixels, w, h = loader(path)
        if flip:
            orig = pixels
            pixels = [[orig[y][w - 1 - x] for x in range(w)] for y in range(h)]
        grid = sample_cells(lambda x, y: pixels[y][x], w, h)
        if p["phase"] not in phases:
            phases[p["phase"]] = []
            order.append(p["phase"])
        phases[p["phase"]].append(
            {"seq": p["seq"], "file": p["file"], "grid": grid,
             "utc": p.get("host_utc_pulled")})
    return {"order": order,
            "phases": {k: {"grid": _avg_grids([f["grid"] for f in v]),
                           "frames": v} for k, v in phases.items()}}


def _rgb_css(cell) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(v))) for v in cell)


def svg_heatmap(grid, title: str) -> str:
    s = 52
    parts = [f'<svg width="{4*s+70}" height="{4*s+30}" role="img" '
             f'aria-label="{title}" xmlns="http://www.w3.org/2000/svg">',
             f'<text x="0" y="14" font-size="13" fill="#1a1d21" '
             f'font-family="monospace">{title}</text>']
    for r in range(4):
        for c in range(4):
            x, y = 30 + c * s, 20 + r * s
            parts.append(
                f'<rect x="{x}" y="{y}" width="{s-3}" height="{s-3}" '
                f'fill="{_rgb_css(grid[r][c])}"/>'
                f'<text x="{x+5}" y="{y+17}" font-size="11" '
                f'fill="#ffffff" font-family="monospace">'
                f'{cell_name(r, c)}</text>'
                f'<text x="{x+5}" y="{y+33}" font-size="10" '
                f'fill="#ffffff" font-family="monospace">'
                f'{_brightness(grid[r][c]):.0f}</text>')
    parts.append("</svg>")
    return "".join(parts)


def svg_delta_chart(cmp_result: dict, title: str) -> str:
    cells = sorted(cmp_result["cells"], key=lambda x: -x["rgb_delta"])
    bw, bh, gap = 34, 150, 6
    width = 30 + len(cells) * (bw + gap)
    mx = max((c["rgb_delta"] for c in cells), default=1) or 1
    parts = [f'<svg width="{width}" height="{bh+70}" role="img" '
             f'aria-label="{title}" xmlns="http://www.w3.org/2000/svg">',
             f'<text x="0" y="14" font-size="13" fill="#1a1d21" '
             f'font-family="monospace">{title}</text>']
    for i, cell in enumerate(cells):
        hgt = bh * cell["rgb_delta"] / mx
        x = 30 + i * (bw + gap)
        y = 20 + (bh - hgt)
        parts.append(
            f'<rect x="{x}" y="{y:.0f}" width="{bw}" height="{hgt:.0f}" '
            f'fill="#0e7c86"/>'
            f'<text x="{x}" y="{20+bh+15}" font-size="10" fill="#1a1d21" '
            f'font-family="monospace">{cell["cell"]}</text>'
            f'<text x="{x}" y="{y-4:.0f}" font-size="9" fill="#1a1d21" '
            f'font-family="monospace">{cell["rgb_delta"]:.0f}</text>')
    parts.append("</svg>")
    return "".join(parts)


def build_report(session_dir, out_dir, loader, flip: bool = True) -> dict:
    """Write report.html + stats.json; returns the stats dict."""
    d, out = Path(session_dir), Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    data = load_session_phases(d, loader, flip=flip)
    order = data["order"]
    if len(order) < 1:
        raise ValueError("no still frames in session manifest")
    first, last = order[0], order[-1]
    cmp_result = (compare_grids(data["phases"][first]["grid"],
                                data["phases"][last]["grid"])
                  if first != last else None)
    stats = {"session": str(d), "phases": order,
             "frames_per_phase": {k: len(v["frames"])
                                  for k, v in data["phases"].items()},
             "first_phase": first, "last_phase": last,
             "comparison": cmp_result}
    (out / "stats.json").write_text(json.dumps(stats, indent=1))
    svgs = [svg_heatmap(data["phases"][p]["grid"], f"phase: {p}")
            for p in order]
    if cmp_result:
        svgs.append(svg_delta_chart(
            cmp_result, f"per-cell RGB change {first} -> {last}"))
    phase_rows = "".join(
        f"<tr><td>{p}</td><td>{len(data['phases'][p]['frames'])}</td>"
        f"<td>{data['phases'][p]['frames'][0]['utc']}</td></tr>"
        for p in order)
    cmp_html = ""
    if cmp_result:
        cmp_html = (f"<p>Mean per-cell RGB change: "
                    f"<strong>{cmp_result['mean_rgb_delta']}</strong>; "
                    f"max {cmp_result['max_rgb_delta']}; cells changed "
                    f"(delta &gt; 25): {cmp_result['cells_changed_over_25']}"
                    f" of 16.</p>")
    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Wall report - {d.name}</title>
<style>
body {{ font-family: ui-monospace, monospace; background: #f4f4f2;
color: #1a1d21; margin: 2rem; }}
table {{ border-collapse: collapse; }} td, th {{ border: 1px solid #999;
padding: 4px 10px; text-align: left; }}
figure {{ margin: 1rem 0; }} img {{ max-width: 48%; }}
</style></head><body>
<h1>Wall report: {d.name}</h1>
<p>Human comparison view for one observed mission. Per-cell values are
mean brightness (0-255) under each cell name; the chart shows per-cell
RGB change between the first and last phase. Colour is never the only
encoding: every value is also printed as a number.</p>
<h2>Phases</h2>
<table><tr><th>phase</th><th>still frames</th><th>first frame UTC</th></tr>
{phase_rows}</table>
<h2>First vs last</h2>
{cmp_html}
{''.join(f'<figure>{s}</figure>' for s in svgs)}
<h2>Data</h2>
<p>Full numbers: <code>stats.json</code> in this directory. Frames and
their sha256 manifest live in the session directory; verify with
<code>kulira wall verify --session &lt;dir&gt;</code>.</p>
</body></html>"""
    (out / "report.html").write_text(html)
    stats["report"] = str(out / "report.html")
    return stats
