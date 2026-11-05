"""Wall report: cell sampling, comparison, HTML/SVG generation."""
import json

from kulira_core.log import verify_log
from kulira_core.wall_observer import WallSession
from test_wall_observer import FakeAdb
from kulira_core.wall_report import (
    build_report, cell_name, compare_grids, sample_cells,
)


def _pixels(w=80, h=80, changed=None):
    rows = []
    for y in range(h):
        row = []
        for x in range(w):
            r = c = 10
            if changed and x > w * 0.75 and y < h * 0.25:
                row.append((200, 200, 200))
            else:
                row.append((10, 20, 30))
        rows.append(row)
    return rows


def _loader_factory(grids_by_name):
    def loader(path):
        px = grids_by_name[path.name]
        return px, len(px[0]), len(px)
    return loader


def test_cell_names():
    assert cell_name(0, 0) == "D1" and cell_name(3, 3) == "A4"


def test_sample_and_compare_detects_change():
    a = sample_cells(lambda x, y: _pixels()[y][x], 80, 80)
    b = sample_cells(lambda x, y: _pixels(changed=True)[y][x], 80, 80)
    cmp_ = compare_grids(a, b)
    assert cmp_["cells_changed_over_25"] >= 1
    top = max(cmp_["cells"], key=lambda c: c["rgb_delta"])
    assert top["cell"] in ("D4", "D3", "C4")  # top-right after sampling


def test_build_report_from_session(tmp_path):
    s = WallSession(tmp_path / "sess", "m1", FakeAdb())
    s.mark("beginning")
    s.capture_still("beginning", burst=1, burst_gap_s=0)
    s.mark("end")
    s.capture_still("end", burst=1, burst_gap_s=0)
    s.close()
    names = [f.name for f in sorted((tmp_path / "sess" / "frames").glob("*.jpg"))]
    # FakeAdb writes identical bytes; loader ignores content anyway.
    loader = _loader_factory({n: _pixels() for n in names})
    stats = build_report(tmp_path / "sess", tmp_path / "rep", loader,
                         flip=False)
    assert stats["phases"] == ["beginning", "end"]
    assert stats["comparison"]["mean_rgb_delta"] == 0.0
    html = (tmp_path / "rep" / "report.html").read_text()
    assert "D1" in html and "A4" in html and "<svg" in html
    assert json.loads((tmp_path / "rep" / "stats.json").read_text())
    verify_log(tmp_path / "sess" / "manifest.jsonl")
