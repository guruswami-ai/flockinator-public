"""Wall tiles: placement map, split/verify, orientation recorded."""
import pytest

from kulira_core.tiles import (
    node_at, split_graphic, tile_positions, verify_tiles, write_ppm,
)


def test_node_map_corners():
    assert node_at(0, 0) == "D1" and node_at(3, 3) == "A4"
    pos = tile_positions(64)
    assert len(pos) == 16 and pos[0]["x"] == 0 and pos[-1]["x"] == 192


def _graphic(path, size=256):
    # quadrant colours make placement/flips observable
    px = []
    for y in range(size):
        row = []
        for x in range(size):
            row.append((255 if x >= size // 2 else 0,
                        255 if y >= size // 2 else 0, 128))
        px.append(row)
    write_ppm(path, px, size, size)


def test_split_and_verify(tmp_path):
    src = tmp_path / "wall.ppm"; _graphic(src)
    m = split_graphic(src, tmp_path / "tiles", flip_horizontal=False)
    assert m["tiles"][0]["node"] == "D1"
    assert verify_tiles(tmp_path / "tiles")["tiles"] == 16


def test_split_rejects_wrong_size(tmp_path):
    src = tmp_path / "bad.ppm"; _graphic(src, size=100)
    with pytest.raises(ValueError, match="must be 256x256"):
        split_graphic(src, tmp_path / "tiles")


def test_flip_is_recorded_and_changes_tiles(tmp_path):
    src = tmp_path / "wall.ppm"; _graphic(src)
    a = split_graphic(src, tmp_path / "a", flip_horizontal=False)
    b = split_graphic(src, tmp_path / "b", flip_horizontal=True)
    assert a["flip_horizontal"] is False and b["flip_horizontal"] is True
    assert a["tiles"][0]["sha256"] != b["tiles"][0]["sha256"]
