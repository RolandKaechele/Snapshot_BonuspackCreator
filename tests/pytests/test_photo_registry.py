"""Tests for photo_registry — registry load/save, ID computation, merge, and conflict detection."""

import json
import os
import pytest
from modules.photo_registry import (
    default_registry_path, load_registry, save_registry,
    parse_id_range, compute_photo_ids, merge_pack_entries, find_conflicts,
)


def test_default_registry_path_points_to_src():
    path = default_registry_path()
    assert os.path.basename(path) == "registry.json"
    assert os.path.basename(os.path.dirname(path)) == "src"


def test_load_registry_missing_file_returns_empty(tmp_path):
    registry = load_registry(str(tmp_path / "nope.json"))
    assert registry == {"entries": []}


def test_save_and_load_registry_round_trip(tmp_path):
    path = str(tmp_path / "sub" / "registry.json")
    data = {"entries": [{"game_id": "snapshot", "pack_name": "p", "photo_id": 1, "photo_name": "a"}]}
    save_registry(data, path)
    assert os.path.exists(path)
    loaded = load_registry(path)
    assert loaded == data


def test_save_registry_writes_utf8_indented_json(tmp_path):
    path = str(tmp_path / "registry.json")
    save_registry({"entries": []}, path)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    assert "\n  " in text  # indent=2 formatting present
    json.loads(text)  # still valid JSON


@pytest.mark.parametrize("id_range,expected", [
    ("100100-100199", (100100, 100199)),
    (" 100100 - 100199 ", (100100, 100199)),
    ("100100", None),
    ("", None),
    ("abc-def", None),
])
def test_parse_id_range(id_range, expected):
    assert parse_id_range(id_range) == expected


def test_compute_photo_ids_assigns_sequential_ids():
    photo_ids = compute_photo_ids("100100-100199", ["photo001", "photo002", "photo003"])
    assert photo_ids == [(100100, "photo001"), (100101, "photo002"), (100102, "photo003")]


def test_compute_photo_ids_invalid_range_returns_empty():
    assert compute_photo_ids("invalid", ["a"]) == []


def test_compute_photo_ids_empty_names_returns_empty():
    assert compute_photo_ids("100100-100199", []) == []


def test_merge_pack_entries_adds_new_pack():
    registry = {"entries": []}
    merge_pack_entries(registry, "snapshot", "mypack", [(100100, "photo001")], source="pack.ini")
    assert len(registry["entries"]) == 1
    entry = registry["entries"][0]
    assert entry["game_id"] == "snapshot"
    assert entry["pack_name"] == "mypack"
    assert entry["photo_id"] == 100100
    assert entry["photo_name"] == "photo001"
    assert entry["source"] == "pack.ini"


def test_merge_pack_entries_replaces_existing_pack_entries():
    registry = {"entries": [
        {"game_id": "snapshot", "pack_name": "mypack", "photo_id": 999, "photo_name": "stale", "source": ""},
    ]}
    merge_pack_entries(registry, "snapshot", "mypack", [(100100, "photo001")])
    assert len(registry["entries"]) == 1
    assert registry["entries"][0]["photo_id"] == 100100


def test_merge_pack_entries_keeps_other_packs_untouched():
    registry = {"entries": [
        {"game_id": "snapshot", "pack_name": "other", "photo_id": 200000, "photo_name": "x", "source": ""},
    ]}
    merge_pack_entries(registry, "snapshot", "mypack", [(100100, "photo001")])
    pack_names = {e["pack_name"] for e in registry["entries"]}
    assert pack_names == {"other", "mypack"}


def test_merge_pack_entries_does_not_cross_game_ids():
    registry = {"entries": [
        {"game_id": "lewdshores", "pack_name": "mypack", "photo_id": 5, "photo_name": "ls", "source": ""},
    ]}
    merge_pack_entries(registry, "snapshot", "mypack", [(100100, "photo001")])
    assert len(registry["entries"]) == 2


def test_find_conflicts_detects_overlapping_photo_id():
    registry = {"entries": [
        {"game_id": "snapshot", "pack_name": "existingpack", "photo_id": 100100, "photo_name": "old"},
    ]}
    photo_ids = [(100100, "newphoto")]
    conflicts = find_conflicts(registry, "snapshot", "newpack", photo_ids)
    assert len(conflicts) == 1
    assert conflicts[0]["pack_name"] == "existingpack"


def test_find_conflicts_ignores_own_pack_name():
    registry = {"entries": [
        {"game_id": "snapshot", "pack_name": "mypack", "photo_id": 100100, "photo_name": "old"},
    ]}
    photo_ids = [(100100, "newphoto")]
    conflicts = find_conflicts(registry, "snapshot", "mypack", photo_ids)
    assert conflicts == []


def test_find_conflicts_ignores_other_game_ids():
    registry = {"entries": [
        {"game_id": "lewdshores", "pack_name": "existingpack", "photo_id": 100100, "photo_name": "old"},
    ]}
    photo_ids = [(100100, "newphoto")]
    conflicts = find_conflicts(registry, "snapshot", "newpack", photo_ids)
    assert conflicts == []


def test_find_conflicts_no_overlap_returns_empty():
    registry = {"entries": [
        {"game_id": "snapshot", "pack_name": "existingpack", "photo_id": 100100, "photo_name": "old"},
    ]}
    photo_ids = [(200000, "newphoto")]
    conflicts = find_conflicts(registry, "snapshot", "newpack", photo_ids)
    assert conflicts == []
