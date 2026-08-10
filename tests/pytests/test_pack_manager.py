"""Tests for PackManager — load, save, new_pack, accessors, and dirty tracking."""

import json
import pytest
from modules.pack_manager import PackManager, _EMPTY_PACK


@pytest.fixture
def pm():
    return PackManager()


def test_new_pack_has_all_default_keys(pm):
    for key in _EMPTY_PACK:
        assert key in pm.data


def test_new_pack_clears_path(pm):
    assert pm.current_path is None


def test_new_pack_resets_data(pm):
    pm.set("title", "My Pack")
    pm.new_pack()
    assert pm.get("title") == ""


def test_new_pack_does_not_share_mutable_defaults():
    pm1 = PackManager()
    pm2 = PackManager()
    pm1.data["photos"].append({"name": "x"})
    assert pm2.data["photos"] == []


def test_get_returns_default_for_missing_key(pm):
    assert pm.get("nonexistent", "fallback") == "fallback"


def test_set_and_get(pm):
    pm.set("title", "Summer Pack")
    assert pm.get("title") == "Summer Pack"


def test_add_photo(pm):
    entry = {"name": "photo1", "source": "/tmp/a.png"}
    pm.add_photo(entry)
    assert pm.data["photos"] == [entry]


def test_add_multiple_photos(pm):
    pm.add_photo({"name": "p1"})
    pm.add_photo({"name": "p2"})
    assert len(pm.data["photos"]) == 2


def test_remove_photo_valid_index(pm):
    pm.add_photo({"name": "p1"})
    pm.add_photo({"name": "p2"})
    pm.remove_photo(0)
    assert pm.data["photos"][0]["name"] == "p2"


def test_remove_photo_invalid_index_is_noop(pm):
    pm.add_photo({"name": "p1"})
    pm.remove_photo(99)
    assert len(pm.data["photos"]) == 1


def test_remove_photo_negative_index_is_noop(pm):
    pm.add_photo({"name": "p1"})
    pm.remove_photo(-1)
    assert len(pm.data["photos"]) == 1


def test_save_and_load_roundtrip(pm, tmp_path):
    pm.set("title", "Test Pack")
    pm.set("id", "testpack")
    pm.set("game", "lewdshores")
    path = str(tmp_path / "pack.json")
    pm.save(path)
    assert pm.current_path == path

    pm2 = PackManager()
    pm2.load(path)
    assert pm2.get("title") == "Test Pack"
    assert pm2.get("id") == "testpack"
    assert pm2.get("game") == "lewdshores"
    assert pm2.current_path == path


def test_save_writes_valid_json(pm, tmp_path):
    pm.set("title", "JSON Check")
    path = str(tmp_path / "pack.json")
    pm.save(path)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["title"] == "JSON Check"


def test_save_is_utf8(pm, tmp_path):
    pm.set("title", "Ünïcödé Pack")
    path = str(tmp_path / "pack.json")
    pm.save(path)
    raw = tmp_path.joinpath("pack.json").read_bytes()
    assert "Ünïcödé Pack".encode("utf-8") in raw


def test_load_merges_missing_keys(pm, tmp_path):
    """A JSON file without all keys must still produce a fully populated data dict."""
    minimal = {"title": "Minimal", "game": "snapshot"}
    path = str(tmp_path / "minimal.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(minimal, f)
    pm.load(path)
    for key in _EMPTY_PACK:
        assert key in pm.data


def test_load_raises_on_missing_file(pm):
    with pytest.raises(FileNotFoundError):
        pm.load("/nonexistent/path/pack.json")


def test_load_raises_on_invalid_json(tmp_path, pm):
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    with pytest.raises(Exception):
        pm.load(str(bad))


# ── New fields added in this release ────────────────────────────────────────

def test_new_pack_has_defaults_fields(pm):
    assert pm.get("defaults_position") == "upskirt"
    assert pm.get("defaults_type") == "plain"
    assert pm.get("defaults_color") == "white"


def test_new_pack_has_event_type(pm):
    assert pm.get("event_type") == "normal"


def test_new_pack_has_special_category_color(pm):
    assert pm.get("special_category_color") == "#dea3a5"


def test_defaults_fields_roundtrip(pm, tmp_path):
    pm.set("defaults_position", "bench")
    pm.set("defaults_type", "kinky")
    pm.set("defaults_color", "black")
    path = str(tmp_path / "pack.json")
    pm.save(path)
    pm2 = PackManager()
    pm2.load(path)
    assert pm2.get("defaults_position") == "bench"
    assert pm2.get("defaults_type") == "kinky"
    assert pm2.get("defaults_color") == "black"


def test_event_type_roundtrip(pm, tmp_path):
    pm.set("event_type", "explosion")
    path = str(tmp_path / "pack.json")
    pm.save(path)
    pm2 = PackManager()
    pm2.load(path)
    assert pm2.get("event_type") == "explosion"


def test_special_category_color_roundtrip(pm, tmp_path):
    pm.set("special_category_color", "#ff0080")
    path = str(tmp_path / "pack.json")
    pm.save(path)
    pm2 = PackManager()
    pm2.load(path)
    assert pm2.get("special_category_color") == "#ff0080"


# ── Dirty tracking ───────────────────────────────────────────────────────────

def test_new_pack_is_not_dirty(pm):
    assert not pm.is_dirty


def test_setitem_marks_dirty(pm):
    pm.data["title"] = "changed"
    assert pm.is_dirty


def test_set_marks_dirty(pm):
    pm.set("title", "changed")
    assert pm.is_dirty


def test_mark_dirty_explicit(pm):
    pm.mark_dirty()
    assert pm.is_dirty


def test_new_pack_clears_dirty(pm):
    pm.set("title", "changed")
    assert pm.is_dirty
    pm.new_pack()
    assert not pm.is_dirty


def test_save_clears_dirty(pm, tmp_path):
    pm.set("title", "changed")
    path = str(tmp_path / "pack.json")
    pm.save(path)
    assert not pm.is_dirty


def test_load_clears_dirty(pm, tmp_path):
    path = str(tmp_path / "pack.json")
    pm.save(path)
    pm.set("title", "changed")
    assert pm.is_dirty
    pm.load(path)
    assert not pm.is_dirty


def test_data_update_marks_dirty(pm):
    pm.data.update({"title": "batch"})
    assert pm.is_dirty


def test_data_delete_marks_dirty(pm):
    pm.data["title"] = "x"
    pm.new_pack()          # reset dirty
    del pm.data["title"]
    assert pm.is_dirty


def test_data_pop_marks_dirty(pm):
    pm.data["title"] = "x"
    pm.new_pack()
    pm.data.pop("title", None)
    assert pm.is_dirty


def test_data_setdefault_marks_dirty_for_new_key(pm):
    pm.data.pop("title", None)
    pm.new_pack()          # title is back from defaults, reset dirty
    pm.data.setdefault("__new_key__", "v")
    assert pm.is_dirty


def test_data_setdefault_no_dirty_for_existing_key(pm):
    # setdefault on an already-present key must NOT flip dirty
    assert "title" in pm.data
    pm.data.setdefault("title", "ignored")
    assert not pm.is_dirty
