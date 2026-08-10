"""Tests for the pure helper functions in import_export module."""

import configparser
import os
import re
import pytest

# Import only the private helpers — no Qt required
from modules.import_export import (
    _read_pack_ini, _write_pack_ini, _export_photo_files,
    _resolve_ini_paths, _inject_end_events,
)


# ── _write_pack_ini ──────────────────────────────────────────────────────────

def test_write_pack_ini_snapshot_creates_file(tmp_path):
    data = {
        "game": "snapshot",
        "pack_type": "photos",
        "id": "mypack",
        "id_range": "110400-110499",
        "title": "My Pack",
        "special_category": "",
        "special_category_color": "#dea3a5",
        "photos": [],
    }
    _write_pack_ini(str(tmp_path), data)
    assert (tmp_path / "pack.ini").exists()


def test_write_pack_ini_snapshot_section(tmp_path):
    data = {
        "game": "snapshot",
        "pack_type": "photos",
        "id": "mypack",
        "id_range": "110400-110499",
        "title": "Summer Pack",
        "special_category": "",
        "special_category_color": "#dea3a5",
        "photos": [],
    }
    _write_pack_ini(str(tmp_path), data)
    content = (tmp_path / "pack.ini").read_text(encoding="utf-8")
    assert "[Mod]" in content
    assert "plugID=snapshot" in content
    assert "id=mypack" in content
    assert "idrange=110400-110499" in content


def test_write_pack_ini_lewdshores_section(tmp_path):
    data = {
        "game": "lewdshores",
        "pack_type": "photos",
        "id": "lewdpack",
        "id_range": "104100-104199",
        "title": "Lewd Pack",
        "special_category": "",
        "special_category_color": "#8bb584",
        "photos": [],
    }
    _write_pack_ini(str(tmp_path), data)
    content = (tmp_path / "pack.ini").read_text(encoding="utf-8")
    assert "[Pack]" in content
    assert "gameID=lewdshores" in content
    assert "id=lewdpack" in content


def test_write_pack_ini_photos_section(tmp_path):
    data = {
        "game": "snapshot",
        "pack_type": "photos",
        "id": "pk",
        "id_range": "110000-110009",
        "title": "T",
        "special_category": "",
        "special_category_color": "#000000",
        "photos": [
            {"name": "pk1", "position": "upskirt", "type": "plain", "color": "white", "source": None},
            {"name": "pk2", "position": "bench", "type": "kinky", "color": "pink", "source": None},
        ],
    }
    _write_pack_ini(str(tmp_path), data)
    content = (tmp_path / "pack.ini").read_text(encoding="utf-8")
    assert "[Photos]" in content
    assert "names=pk1,pk2" in content
    assert "pk1.position=upskirt" in content
    assert "pk2.type=kinky" in content


def test_write_pack_ini_events_type(tmp_path):
    data = {
        "game": "snapshot",
        "pack_type": "events",
        "id": "evpack",
        "id_range": "113900-113910",
        "title": "Event Pack",
        "special_category": "",
        "special_category_color": "#000000",
        "photos": [],
    }
    _write_pack_ini(str(tmp_path), data)
    content = (tmp_path / "pack.ini").read_text(encoding="utf-8")
    assert "type=events" in content


def test_write_pack_ini_special_category(tmp_path):
    data = {
        "game": "snapshot",
        "pack_type": "photos",
        "id": "pk",
        "id_range": "110000-110009",
        "title": "T",
        "special_category": "Bikini",
        "special_category_color": "#dea3a5",
        "photos": [],
    }
    _write_pack_ini(str(tmp_path), data)
    content = (tmp_path / "pack.ini").read_text(encoding="utf-8")
    assert 'specialCategory="Bikini"' in content
    assert "specialCategoryColor=dea3a5" in content


# ── _read_pack_ini ───────────────────────────────────────────────────────────

def _make_ini(tmp_path, lines):
    ini = tmp_path / "pack.ini"
    ini.write_text("\n".join(lines), encoding="utf-8")
    return str(ini)


def test_read_pack_ini_snapshot_game(tmp_path):
    ini = _make_ini(tmp_path, [
        "[Mod]", "plugID=snapshot", "id=mypack", "idrange=110400-110499", 'title="My Pack"',
        "[Photos]", "names=",
    ])
    data = _read_pack_ini(ini, str(tmp_path))
    assert data["game"] == "snapshot"
    assert data["id"] == "mypack"
    assert data["id_range"] == "110400-110499"
    assert data["title"] == "My Pack"


def test_read_pack_ini_lewdshores_game(tmp_path):
    ini = _make_ini(tmp_path, [
        "[Pack]", "gameID=lewdshores", "id=lewdpack", "idrange=104100-104199", 'title="Lewd Pack"',
    ])
    data = _read_pack_ini(ini, str(tmp_path))
    assert data["game"] == "lewdshores"


def test_read_pack_ini_detects_lovelens(tmp_path):
    ini = _make_ini(tmp_path, [
        "[Mod]", "plugID=snapshot", "id=ll", "idrange=110000-110009", 'title="LL"',
        "[Hypnosis]", "model=slim",
        "[Photos]", "names=",
    ])
    data = _read_pack_ini(ini, str(tmp_path))
    assert data["pack_type"] == "lovelens"


def test_read_pack_ini_detects_events(tmp_path):
    ini = _make_ini(tmp_path, [
        "[Mod]", "plugID=snapshot", "id=ev", "idrange=113900-113910", 'title="EV"',
        "type=events",
    ])
    data = _read_pack_ini(ini, str(tmp_path))
    assert data["pack_type"] == "events"


def test_read_pack_ini_parses_photos(tmp_path):
    ini = _make_ini(tmp_path, [
        "[Mod]", "plugID=snapshot", "id=pk", "idrange=110000-110009", 'title="T"',
        "[Photos]",
        "names=pk1,pk2",
        "pk1.position=upskirt",
        "pk1.type=plain",
        "pk1.color=white",
        "pk2.position=bench",
        "pk2.type=kinky",
        "pk2.color=pink",
    ])
    data = _read_pack_ini(ini, str(tmp_path))
    photos = data["photos"]
    assert len(photos) == 2
    assert photos[0]["name"] == "pk1"
    assert photos[0]["position"] == "upskirt"
    assert photos[1]["color"] == "pink"


def test_read_pack_ini_photo_source_none_when_file_missing(tmp_path):
    ini = _make_ini(tmp_path, [
        "[Mod]", "plugID=snapshot", "id=pk", "idrange=110000-110009", 'title="T"',
        "[Photos]", "names=pk1",
    ])
    data = _read_pack_ini(ini, str(tmp_path))
    assert data["photos"][0]["source"] is None


def test_read_pack_ini_photo_source_set_when_dat_exists(tmp_path):
    data_dir = tmp_path / "Data"
    data_dir.mkdir()
    (data_dir / "pk1.dat").write_bytes(b"\x00")
    ini = _make_ini(tmp_path, [
        "[Mod]", "plugID=snapshot", "id=pk", "idrange=110000-110009", 'title="T"',
        "[Photos]", "names=pk1",
    ])
    data = _read_pack_ini(ini, str(tmp_path))
    assert data["photos"][0]["source"] is not None


# ── _export_photo_files ──────────────────────────────────────────────────────

def test_export_photo_files_copies_existing(tmp_path):
    src_img = tmp_path / "img.png"
    src_img.write_bytes(b"\x89PNG")
    data_dir = tmp_path / "Data"
    data_dir.mkdir()
    pack_data = {
        "photos": [{"name": "pk1", "source": str(src_img)}]
    }
    _export_photo_files(str(data_dir), pack_data)
    # extension is preserved from source file
    assert (data_dir / "pk1.png").exists()


def test_export_photo_files_skips_missing_source(tmp_path):
    data_dir = tmp_path / "Data"
    data_dir.mkdir()
    pack_data = {
        "photos": [{"name": "pk1", "source": "/nonexistent/file.png"}]
    }
    _export_photo_files(str(data_dir), pack_data)
    assert not (data_dir / "pk1.dat").exists()


def test_export_photo_files_skips_none_source(tmp_path):
    data_dir = tmp_path / "Data"
    data_dir.mkdir()
    pack_data = {"photos": [{"name": "pk1", "source": None}]}
    _export_photo_files(str(data_dir), pack_data)
    assert not (data_dir / "pk1.dat").exists()


# ── _resolve_ini_paths ───────────────────────────────────────────────────────

def test_resolve_ini_paths_prefers_pack_ini(tmp_path):
    (tmp_path / "pack.ini").write_text("[Mod]\n", encoding="utf-8")
    (tmp_path / "other.ini").write_text("[Mod]\n", encoding="utf-8")
    result = _resolve_ini_paths(str(tmp_path), None)
    # pack.ini is first; all inis are returned
    assert result[0] == str(tmp_path / "pack.ini")
    assert len(result) >= 1


def test_resolve_ini_paths_returns_all_when_no_pack_ini(tmp_path):
    (tmp_path / "part1.ini").write_text("[Mod]\n", encoding="utf-8")
    (tmp_path / "part2.ini").write_text("[Mod]\n", encoding="utf-8")
    result = _resolve_ini_paths(str(tmp_path), None)
    assert len(result) == 2
    assert all(p.endswith(".ini") for p in result)


def test_resolve_ini_paths_returns_empty_for_no_ini(tmp_path, monkeypatch):
    monkeypatch.setattr("modules.import_export.show_warning", lambda *a, **kw: None)
    result = _resolve_ini_paths(str(tmp_path), None)
    assert result == []


# ── multi-ini split export ───────────────────────────────────────────────────

def test_write_pack_ini_splits_at_100(tmp_path):
    photos = [{"name": f"p{i}", "position": "upskirt", "type": "plain",
               "color": "white", "source": None} for i in range(150)]
    data = {
        "game": "snapshot", "pack_type": "photos",
        "id": "bigpack", "id_range": "110000-110099", "title": "Big",
        "special_category": "", "special_category_color": "#000000",
        "photos": photos,
    }
    _write_pack_ini(str(tmp_path), data)
    inis = sorted(f for f in os.listdir(tmp_path) if f.endswith(".ini"))
    assert inis == ["bigpack1.ini", "bigpack2.ini"]


def test_write_pack_ini_split_ids_and_titles(tmp_path):
    photos = [{"name": f"p{i}", "position": "upskirt", "type": "plain",
               "color": "white", "source": None} for i in range(110)]
    data = {
        "game": "snapshot", "pack_type": "photos",
        "id": "mypack", "id_range": "110000-110099", "title": "My Pack",
        "special_category": "", "special_category_color": "#000000",
        "photos": photos,
    }
    _write_pack_ini(str(tmp_path), data)
    c1 = (tmp_path / "mypack1.ini").read_text(encoding="utf-8")
    c2 = (tmp_path / "mypack2.ini").read_text(encoding="utf-8")
    assert "id=mypack1" in c1
    assert 'title="My Pack Part 1"' in c1
    assert "id=mypack2" in c2
    assert 'title="My Pack Part 2"' in c2


def test_write_pack_ini_split_idrange_increments(tmp_path):
    photos = [{"name": f"p{i}", "position": "upskirt", "type": "plain",
               "color": "white", "source": None} for i in range(110)]
    data = {
        "game": "snapshot", "pack_type": "photos",
        "id": "pk", "id_range": "111700-111799", "title": "T",
        "special_category": "", "special_category_color": "#000000",
        "photos": photos,
    }
    _write_pack_ini(str(tmp_path), data)
    c1 = (tmp_path / "pk1.ini").read_text(encoding="utf-8")
    c2 = (tmp_path / "pk2.ini").read_text(encoding="utf-8")
    assert "idrange=111700-111799" in c1
    assert "idrange=111800-111899" in c2


def test_write_pack_ini_no_split_below_100(tmp_path):
    photos = [{"name": f"p{i}", "position": "upskirt", "type": "plain",
               "color": "white", "source": None} for i in range(99)]
    data = {
        "game": "snapshot", "pack_type": "photos",
        "id": "small", "id_range": "110000-110099", "title": "Small",
        "special_category": "", "special_category_color": "#000000",
        "photos": photos,
    }
    _write_pack_ini(str(tmp_path), data)
    assert (tmp_path / "pack.ini").exists()
    assert not (tmp_path / "small1.ini").exists()


# ── Special Traits and aliases ───────────────────────────────────────────────

def test_read_special_traits(tmp_path):
    ini = _make_ini(tmp_path, [
        "[Mod]", "plugID=snapshot", "id=pk", "idrange=110000-110099", 'title="T"',
        "[Special Traits]",
        'specialType="Thong",thongs,piercing',
        'specialType="Busted!",busted,kinky',
        'specialColor="Alice",alice,white',
    ])
    data = _read_pack_ini(ini, str(tmp_path))
    assert len(data["special_types"]) == 2
    assert len(data["special_colors"]) == 1


def test_read_special_type_alias(tmp_path):
    ini = _make_ini(tmp_path, [
        "[Mod]", "plugID=snapshot", "id=pk", "idrange=110000-110099", 'title="T"',
        "[Special Type]",
        'specialType="Yoga",yoga,kinky',
    ])
    data = _read_pack_ini(ini, str(tmp_path))
    assert len(data.get("special_types", [])) == 1


def test_read_create_your_own_traits_alias(tmp_path):
    ini = _make_ini(tmp_path, [
        "[Mod]", "plugID=snapshot", "id=pk", "idrange=110000-110099", 'title="T"',
        "[Create your own traits]",
        'newType="Swimsuit",swimsuit,kinky',
    ])
    data = _read_pack_ini(ini, str(tmp_path))
    assert len(data.get("special_types", [])) == 1


def test_write_special_traits_roundtrip(tmp_path):
    ini = _make_ini(tmp_path, [
        "[Mod]", "plugID=snapshot", "id=pk", "idrange=110000-110099", 'title="T"',
        "[Special Traits]",
        'specialType="Thong",thongs,piercing',
        'specialColor="Alice",alice,white',
    ])
    data = _read_pack_ini(ini, str(tmp_path))
    out = tmp_path / "out"
    out.mkdir()
    _write_pack_ini(str(out), data)
    content = (out / "pack.ini").read_text(encoding="utf-8")
    assert "[Special Traits]" in content
    assert 'specialType="Thong",thongs,piercing' in content
    assert 'specialColor="Alice",alice,white' in content


# ── Passthrough sections ─────────────────────────────────────────────────────

def test_read_passthrough_stores_unknown_section(tmp_path):
    # [Defaults] is now a structured section (not passthrough).
    # Extra keys within [Defaults] that the app doesn't know about are simply ignored.
    ini = _make_ini(tmp_path, [
        "[Mod]", "gameID=snapshot", "id=pk", "idrange=110000-110099", 'title="T"',
        "[Defaults]",
        "position=jogger",
        "packtheme=Yoga",
        "themecolor=ff0000",
        "[Photos]", "names=",
    ])
    data = _read_pack_ini(ini, str(tmp_path))
    # [Defaults] structured fields are read
    assert data.get("defaults_position") == "jogger"
    # [Defaults] must NOT appear in passthrough_sections
    headers = [h for h, _ in data.get("passthrough_sections", [])]
    assert "[Defaults]" not in headers


def test_read_passthrough_hypnosis_section(tmp_path):
    # [Hypnosis] is now parsed into love_lens / overlays structured data, not passthrough.
    ini = _make_ini(tmp_path, [
        "[Mod]", "plugID=snapshot", "id=ll", "idrange=110000-110099", 'title="T"',
        "[Hypnosis]",
        "model=slim",
        "hairstyle=short",
        "[Photos]", "names=",
    ])
    data = _read_pack_ini(ini, str(tmp_path))
    headers = [h for h, _ in data.get("passthrough_sections", [])]
    assert "[Hypnosis]" not in headers
    assert data.get("love_lens") == {"model": "slim", "hairStyle": "short"}


def test_write_passthrough_section_verbatim(tmp_path):
    # [Hypnosis] is now generated from structured love_lens data, not passthrough.
    ini = _make_ini(tmp_path, [
        "[Mod]", "gameID=snapshot", "id=pk", "idrange=110000-110099", 'title="T"',
        "[Hypnosis]",
        "model=slim",
        "overlayStart=ov1",
        "[Photos]", "names=",
    ])
    data = _read_pack_ini(ini, str(tmp_path))
    data["pack_type"] = "lovelens"
    out = tmp_path / "out"
    out.mkdir()
    _write_pack_ini(str(out), data)
    content = (out / "pack.ini").read_text(encoding="utf-8")
    assert "[Hypnosis]" in content
    assert "model=slim" in content
    assert "overlayStart=ov1" in content


def test_regen_sections_not_in_passthrough(tmp_path):
    ini = _make_ini(tmp_path, [
        "[Mod]", "plugID=snapshot", "id=pk", "idrange=110000-110099", 'title="T"',
        "[Special Traits]",
        'specialType="X",x,kinky',
        "[Photos]", "names=",
    ])
    data = _read_pack_ini(ini, str(tmp_path))
    headers = [h for h, _ in data.get("passthrough_sections", [])]
    assert "[Special Traits]" not in headers
    assert "[Mod]" not in headers
    assert "[Photos]" not in headers


# ── Bare continuation line fix ───────────────────────────────────────────────

def test_read_bare_continuation_line_tolerated(tmp_path):
    ini = _make_ini(tmp_path, [
        "[Mod]", "plugID=snapshot", "id=pk", "idrange=110000-110099",
        'title="T"',
        "[Photos]",
        "names=pk1",
        "pk1.type=plain,stripes,dots,frill,kinky,none,plug,piercing,cum,nude,",
        "flashing",  # bare continuation — no leading space
    ])
    # Should not raise
    data = _read_pack_ini(ini, str(tmp_path))
    assert data["game"] == "snapshot"


# ── Image format lookup ──────────────────────────────────────────────────────

@pytest.mark.parametrize("ext", [".dat", ".jpa", ".pna", ".png", ".jpg", ".jpeg"])
def test_read_photo_source_finds_all_extensions(tmp_path, ext):
    data_dir = tmp_path / "Data"
    data_dir.mkdir()
    (data_dir / f"pk1{ext}").write_bytes(b"\x00")
    ini = _make_ini(tmp_path, [
        "[Mod]", "plugID=snapshot", "id=pk", "idrange=110000-110099", 'title="T"',
        "[Photos]", "names=pk1",
    ])
    data = _read_pack_ini(ini, str(tmp_path))
    assert data["photos"][0]["source"] is not None
    assert data["photos"][0]["source"].endswith(ext)


def test_read_photo_source_falls_back_to_pack_root(tmp_path):
    (tmp_path / "pk1.png").write_bytes(b"\x89PNG")
    ini = _make_ini(tmp_path, [
        "[Mod]", "plugID=snapshot", "id=pk", "idrange=110000-110099", 'title="T"',
        "[Photos]", "names=pk1",
    ])
    data = _read_pack_ini(ini, str(tmp_path))
    assert data["photos"][0]["source"] is not None


# ── _inject_end_events ───────────────────────────────────────────────────────

def _make_dialog_json(node_count=1, has_end_event=False):
    import json
    data = {}
    for i in range(node_count):
        data[f"nd_ID_{i}"] = i
        data[f"nd_tag_{i}"] = "NPC"
        data[f"nd_text_{i}"] = f"line {i}"
        data[f"nd_extraData_{i}"] = ""
        data[f"nd_oNPC_{i}"] = -1
        data[f"nd_oSet_{i}"] = -1
        data[f"nd_oAct_{i}"] = -1
        data[f"nd_expand_{i}"] = True
        data[f"nd_rect_{i}"] = [0, 0]
        if i == node_count - 1 and has_end_event:
            data[f"nd_vars{i}"] = 1
            data[f"nd_varKey_{i}_0"] = "endEvent"
            data[f"nd_var_{i}_0"] = ""
        else:
            data[f"nd_vars{i}"] = 0
    data["npcDiags"] = node_count
    data["playerDiags"] = 0
    return json.dumps(data)


def test_inject_end_events_adds_to_last_node():
    import json
    pack_data = {
        "events": [
            {"type": "dialog", "name": "scene_01", "content": _make_dialog_json(3)},
        ]
    }
    _inject_end_events(pack_data, {"scene_01"})
    result = json.loads(pack_data["events"][0]["content"])
    last_idx = 2
    assert result[f"nd_vars{last_idx}"] == 1
    assert result[f"nd_varKey_{last_idx}_0"] == "endEvent"


def test_inject_end_events_skips_already_present():
    import json
    pack_data = {
        "events": [
            {"type": "dialog", "name": "scene_01",
             "content": _make_dialog_json(2, has_end_event=True)},
        ]
    }
    _inject_end_events(pack_data, {"scene_01"})
    result = json.loads(pack_data["events"][0]["content"])
    # Still exactly one endEvent var on last node
    assert result["nd_vars1"] == 1


def test_inject_end_events_skips_non_matching_scene():
    import json
    original = _make_dialog_json(2)
    pack_data = {
        "events": [
            {"type": "dialog", "name": "other_scene", "content": original},
        ]
    }
    _inject_end_events(pack_data, {"scene_01"})
    assert pack_data["events"][0]["content"] == original


def test_inject_end_events_ignores_non_dialog_events():
    pack_data = {
        "events": [
            {"type": "background", "name": "scene_01", "source": "/some/file.dat"},
        ]
    }
    _inject_end_events(pack_data, {"scene_01"})
    # No crash, event unchanged
    assert pack_data["events"][0]["type"] == "background"


# ── per-part trait lists ─────────────────────────────────────────────────────

def test_write_pack_ini_uses_per_part_traits(tmp_path):
    photos = [{"name": f"p{i}", "position": "upskirt", "type": "plain",
               "color": "white", "source": None} for i in range(110)]
    data = {
        "game": "snapshot", "pack_type": "photos",
        "id": "pk", "id_range": "110000-110099", "title": "T",
        "special_category": "", "special_category_color": "#000000",
        "photos": photos,
        "special_types":  ['"A",a,kinky', '"B",b,kinky', '"C",c,kinky'],
        "special_colors": ['"X",x,white', '"Y",y,white'],
        # part 0 gets only A; part 1 gets only B,C
        "special_types_parts":  [['"A",a,kinky'], ['"B",b,kinky', '"C",c,kinky']],
        "special_colors_parts": [['"X",x,white'], ['"Y",y,white']],
    }
    _write_pack_ini(str(tmp_path), data)
    c1 = (tmp_path / "pk1.ini").read_text(encoding="utf-8")
    c2 = (tmp_path / "pk2.ini").read_text(encoding="utf-8")
    assert 'specialType="A",a,kinky' in c1
    assert 'specialType="B"' not in c1
    assert 'specialType="B",b,kinky' in c2
    assert 'specialType="A"' not in c2
    assert 'specialColor="X",x,white' in c1
    assert 'specialColor="Y",y,white' in c2


def test_write_pack_ini_falls_back_to_flat_traits_when_no_parts(tmp_path):
    data = {
        "game": "snapshot", "pack_type": "photos",
        "id": "pk", "id_range": "110000-110099", "title": "T",
        "special_category": "", "special_category_color": "#000000",
        "photos": [],
        "special_types": ['"A",a,kinky'],
        "special_colors": [],
    }
    _write_pack_ini(str(tmp_path), data)
    content = (tmp_path / "pack.ini").read_text(encoding="utf-8")
    assert 'specialType="A",a,kinky' in content


# ── _type_key per-photo roundtrip ────────────────────────────────────────────

def test_read_photo_newtype_sets_type_key(tmp_path):
    ini = _make_ini(tmp_path, [
        "[Pack]", "gameID=lewdshores", "id=pk", "idrange=104100-104199", 'title="T"',
        "[Photos]", "names=pk1",
        "pk1.newType=front view",
    ])
    data = _read_pack_ini(ini, str(tmp_path))
    ph = data["photos"][0]
    assert ph["type"] == "front view"
    assert ph.get("_type_key") == "newType"


def test_write_photo_newtype_key_preserved(tmp_path):
    data = {
        "game": "lewdshores", "pack_type": "photos",
        "id": "pk", "id_range": "104100-104199", "title": "T",
        "special_category": "", "special_category_color": "#000000",
        "photos": [{"name": "pk1", "type": "front view", "_type_key": "newType", "source": None}],
    }
    _write_pack_ini(str(tmp_path), data)
    content = (tmp_path / "pack.ini").read_text(encoding="utf-8")
    assert "pk1.newType=front view" in content
    assert "pk1.type=" not in content


def test_write_photo_type_key_default(tmp_path):
    data = {
        "game": "lewdshores", "pack_type": "photos",
        "id": "pk", "id_range": "104100-104199", "title": "T",
        "special_category": "", "special_category_color": "#000000",
        "photos": [{"name": "pk1", "type": "front view", "source": None}],
    }
    _write_pack_ini(str(tmp_path), data)
    content = (tmp_path / "pack.ini").read_text(encoding="utf-8")
    assert "pk1.type=front view" in content
