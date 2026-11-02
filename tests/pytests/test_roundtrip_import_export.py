"""Round-trip regression test — import(export(pack)) must reproduce byte-identical
assets and equivalent trait data, catching silent re-encoding/renaming bugs."""

import hashlib
import os

from modules.import_export import (
    _write_pack_ini, _export_photo_files, _resolve_ini_paths, _read_pack_ini,
)


def _sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _make_png(path: str, pixel: tuple[int, int, int]) -> None:
    from PIL import Image  # type: ignore
    Image.new("RGB", (4, 4), pixel).save(path, format="PNG")


def _build_pack_data(img1: str, img2: str) -> dict:
    return {
        "game": "snapshot",
        "pack_type": "photos",
        "id": "rtpack",
        "id_range": "500000-500099",
        "title": "Roundtrip Pack",
        "special_category": "",
        "special_category_color": "#dea3a5",
        "passthrough_sections": [],
        "photos": [
            {"name": "rtpack1", "source": img1, "position": "upskirt",
             "type": "plain", "color": "white"},
            {"name": "rtpack2", "source": img2, "position": "bench",
             "type": "nude", "color": "rare"},
        ],
    }


def test_export_then_import_preserves_photo_assets_and_traits(tmp_path):
    img1 = str(tmp_path / "src1.png")
    img2 = str(tmp_path / "src2.png")
    _make_png(img1, (255, 0, 0))
    _make_png(img2, (0, 255, 0))
    data = _build_pack_data(img1, img2)

    export_folder = str(tmp_path / "exported")
    data_folder = os.path.join(export_folder, "Data")
    os.makedirs(data_folder, exist_ok=True)
    _write_pack_ini(export_folder, data)
    _export_photo_files(data_folder, data)

    ini_paths = _resolve_ini_paths(export_folder, None)
    assert ini_paths
    imported = _read_pack_ini(ini_paths[0], export_folder)

    assert imported["photos"][0]["name"] == "rtpack1"
    assert imported["photos"][1]["name"] == "rtpack2"
    assert imported["photos"][0]["position"] == "upskirt"
    assert imported["photos"][1]["position"] == "bench"
    assert imported["photos"][0]["type"] == "plain"
    assert imported["photos"][1]["type"] == "nude"
    assert imported["photos"][0]["color"] == "white"
    assert imported["photos"][1]["color"] == "rare"

    # Exported asset bytes must exactly match the originals (no re-encoding).
    assert _sha256(imported["photos"][0]["source"]) == _sha256(img1)
    assert _sha256(imported["photos"][1]["source"]) == _sha256(img2)


def test_double_roundtrip_assets_are_byte_identical(tmp_path):
    """Export -> import -> export again; both exports must produce identical asset bytes."""
    img1 = str(tmp_path / "src1.png")
    img2 = str(tmp_path / "src2.png")
    _make_png(img1, (10, 20, 30))
    _make_png(img2, (40, 50, 60))
    data = _build_pack_data(img1, img2)

    folder_a = str(tmp_path / "export_a")
    data_folder_a = os.path.join(folder_a, "Data")
    os.makedirs(data_folder_a, exist_ok=True)
    _write_pack_ini(folder_a, data)
    _export_photo_files(data_folder_a, data)

    ini_paths = _resolve_ini_paths(folder_a, None)
    imported = _read_pack_ini(ini_paths[0], folder_a)

    folder_b = str(tmp_path / "export_b")
    data_folder_b = os.path.join(folder_b, "Data")
    os.makedirs(data_folder_b, exist_ok=True)
    _write_pack_ini(folder_b, imported)
    _export_photo_files(data_folder_b, imported)

    for name in ("rtpack1", "rtpack2"):
        path_a = os.path.join(data_folder_a, f"{name}.png")
        path_b = os.path.join(data_folder_b, f"{name}.png")
        assert os.path.exists(path_a) and os.path.exists(path_b)
        assert _sha256(path_a) == _sha256(path_b)
