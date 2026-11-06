#!/usr/bin/env python3
"""Build the website's panel GIFs from audited-safe animation segments.

Root cause of the 2026-11-06 KILL-on-site bug: previews/recon-hud/horizon.gif
looks like a SCAN animation for its first ~128 frames, then plays a KILL
countdown and KILL FEED LOST. Sampling only early frames is not an audit.

Rule: every website GIF is built ONLY from the frame ranges below, whose
bottom status text was inspected frame-by-frame (every 6th frame strip plus
segment boundaries). Banned sources for the rescue-themed site:
horizon.gif (KILL after f128), signal-lost.gif, events.gif,
close-approach.gif, kill-countdown.gif (KILL/ENGAGE wording throughout).

Source: previews/recon-hud/recon-hud.gif (144 frames), states:
  HOLD 0-23, SCAN 24-47, SEEN 48-71, SHARE 72-95, CHECK 96-119, DOUBT 120-143
Margins of 2 frames are trimmed at both ends of each segment.
Requires Pillow:  uv run --with pillow python3 cloudflare/build_panels.py
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "previews/recon-hud/recon-hud.gif"
OUT = ROOT / "cloudflare/site/panels"
SEGMENTS = {  # name -> (first, last) inclusive, audited safe
    "scan": (26, 45),    # SCAN ALT
    "share": (74, 93),   # SHARE REPORT
    "check": (98, 117),  # CHECK VERIFY
    "doubt": (122, 141), # DOUBT 2 CLAIMS
}
SIZE = 192

def load_frames():
    im = Image.open(SRC)
    frames = []
    for i in range(im.n_frames):
        im.seek(i)
        frames.append((im.convert("RGB"), im.info.get("duration", 80)))
    return frames

def clip(frames, seg, size=SIZE):
    a, b = SEGMENTS[seg]
    out = []
    for f, d in frames[a:b + 1]:
        out.append((f.resize((size, size)).quantize(colors=64, method=Image.MEDIANCUT), d))
    return out

def save_gif(frames, path):
    frames[0][0].save(path, save_all=True, append_images=[f for f, _ in frames[1:]],
                      duration=[d for _, d in frames], loop=0, optimize=True)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frames = load_frames()
    clips = {name: clip(frames, name) for name in SEGMENTS}
    for name, c in clips.items():
        save_gif(c, OUT / f"{name}.gif")
        c[len(c) // 2][0].convert("RGB").save(OUT / f"{name}.png")
        print(name, len(c), "frames")
    # 4x4 montage composed from the same audited clips, offset per cell.
    cell = 96
    montage = []
    base = [clips[k] for k in ("scan", "share", "check", "doubt")]
    total = 24
    for t in range(total):
        canvas = Image.new("RGB", (cell * 4, cell * 4), (5, 12, 10))
        for r in range(4):
            for c in range(4):
                cl = base[(r + c) % 4]
                f = cl[(t + (r * 4 + c) * 3) % len(cl)][0].convert("RGB").resize((cell, cell))
                canvas.paste(f, (c * cell, r * cell))
        montage.append((canvas.quantize(colors=64, method=Image.MEDIANCUT), 120))
    save_gif(montage, OUT / "wall-montage.gif")
    montage[10][0].convert("RGB").save(OUT / "wall-montage.png")
    print("wall-montage", total, "frames")

if __name__ == "__main__":
    main()
