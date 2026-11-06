"""kulira campaign validate|run|stop|report; kulira wall ..."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from .log import verify_log
from .orchestrator import Orchestrator
from .scenario import load_scenario, ScenarioError
from .wall_observer import Adb, WallSession, verify_session

def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="kulira"); sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("campaign"); csub = c.add_subparsers(dest="sub", required=True)
    v = csub.add_parser("validate"); v.add_argument("scenario")
    r = csub.add_parser("run"); r.add_argument("scenario"); r.add_argument("--dry-run", action="store_true"); r.add_argument("--out")
    s = csub.add_parser("stop"); s.add_argument("--run", required=True)
    rp = csub.add_parser("report"); rp.add_argument("--run", required=True)
    w = sub.add_parser("wall"); wsub = w.add_subparsers(dest="sub", required=True)
    wc = wsub.add_parser("capture"); wc.add_argument("--mission", required=True)
    wc.add_argument("--phase", default="beginning")
    wc.add_argument("--mode", choices=["stills", "video"], default="stills")
    wc.add_argument("--burst", type=int, default=3)
    wc.add_argument("--seconds", type=float, default=20.0)
    wc.add_argument("--interval", type=float, default=0.0,
                    help="repeat still bursts every N seconds (0 = once)")
    wc.add_argument("--count", type=int, default=1, help="number of bursts")
    wc.add_argument("--adb", default="adb"); wc.add_argument("--serial")
    wc.add_argument("--telemetry", help="telemetry/journal file to hash-link")
    wc.add_argument("--out", required=True)
    wv = wsub.add_parser("verify"); wv.add_argument("--session", required=True)
    ds = sub.add_parser("dataset"); dsub = ds.add_subparsers(dest="sub", required=True)
    db = dsub.add_parser("build"); db.add_argument("--session", required=True)
    db.add_argument("--telemetry"); db.add_argument("--mission", required=True)
    db.add_argument("--out", required=True)
    dv = dsub.add_parser("verify"); dv.add_argument("--dataset", required=True)
    wr = wsub.add_parser("report"); wr.add_argument("--session", required=True)
    wr.add_argument("--out", required=True); wr.add_argument("--no-flip", action="store_true")
    args = p.parse_args(argv)
    if args.cmd == "dataset":
        from .dataset import build_dataset, verify_dataset
        try:
            if args.sub == "build":
                print(json.dumps(build_dataset(args.session, args.telemetry,
                                               args.out, args.mission), indent=1)); return 0
            print(json.dumps(verify_dataset(args.dataset))); return 0
        except Exception as e:
            print(f"error: {e}", file=sys.stderr); return 1
    if args.cmd == "wall":
        try:
            if args.sub == "verify":
                print(json.dumps(verify_session(args.session))); return 0
            if args.sub == "report":
                from .wall_report import build_report
                def loader(path):
                    try:
                        from PIL import Image
                    except ImportError:
                        raise SystemExit("wall report needs Pillow: uv run --with pillow ...")
                    im = Image.open(path).convert("RGB")
                    im.thumbnail((1200, 1200))
                    w, h = im.size
                    px = im.load()
                    return [[px[x, y] for x in range(w)] for y in range(h)], w, h
                print(json.dumps(build_report(args.session, args.out, loader,
                                              flip=not args.no_flip), indent=1)); return 0
            adb = Adb(args.adb, args.serial)
            s = WallSession(args.out, args.mission, adb, entry_point="cli")
            if args.telemetry:
                th = Path(args.telemetry)
                from .wall_observer import file_sha256
                s.mark("telemetry_linked",
                       f"{th.name} sha256={file_sha256(th) if th.exists() else 'MISSING'}")
            s.open_camera("CAMERA")
            s.mark(args.phase, "capture start")
            for i in range(args.count):
                if args.mode == "video":
                    s.capture_video(args.phase, args.seconds)
                else:
                    s.capture_still(args.phase, burst=args.burst)
                if args.interval and i + 1 < args.count:
                    import time as _t; _t.sleep(args.interval)
            end = s.close("capture complete")
            print(json.dumps({"session": str(args.out),
                              "mission_id": args.mission,
                              "frames": end["payload"]["frames"],
                              "verified": verify_session(args.out)}))
            return 0
        except Exception as e:
            print(f"error: {e}", file=sys.stderr); return 1
    try:
        if args.sub == "validate":
            s = load_scenario(args.scenario); print(f"OK {s.id} seed={s.seed} plane={s.plane} attacks={len(s.attacks)}"); return 0
        if args.sub == "run":
            s = load_scenario(args.scenario)
            out = Path(args.out) if args.out else Path("validation/kulira") / f"{s.id}-{s.seed}"
            report = Orchestrator().run(s, out, dry_run=args.dry_run or not s.authorised)
            print(json.dumps(report)); return 0 if report["state"] == "COMPLETED" else 2
        if args.sub == "stop":
            Path(args.run).mkdir(parents=True, exist_ok=True); (Path(args.run) / "STOP").write_text("stop\n"); print(f"STOP written {args.run}"); return 0
        if args.sub == "report":
            run = Path(args.run); entries = verify_log(run / "attacks.jsonl")
            report = json.loads((run / "report.json").read_text()); report["log_verified"] = True; report["log_entries"] = len(entries)
            print(json.dumps(report, indent=2)); return 0
    except (ScenarioError, Exception) as e:
        print(f"error: {e}", file=sys.stderr); return 1
    return 0

if __name__ == "__main__": raise SystemExit(main())
