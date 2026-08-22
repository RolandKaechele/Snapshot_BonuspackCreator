"""Tests for ai_image_gen — type/modifier dictionaries and dialog logic (no network)."""

import pytest


# ── Module fixture ────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def aig(qapp):  # noqa: ARG001
    import modules.ai_image_gen as m
    return m


# ── PHOTO_TYPES ───────────────────────────────────────────────────────────────

def test_photo_types_has_upskirt(aig):
    assert "upskirt" in aig.PHOTO_TYPES


def test_photo_types_all_have_label_and_prompt(aig):
    for key, info in aig.PHOTO_TYPES.items():
        assert "label" in info, f"PHOTO_TYPES[{key!r}] missing 'label'"
        assert "prompt_enhancement" in info, f"PHOTO_TYPES[{key!r}] missing 'prompt_enhancement'"


# ── LEWD_SHORES_PHOTO_TYPES ───────────────────────────────────────────────────

def test_lewd_shores_photo_types_not_empty(aig):
    assert len(aig.LEWD_SHORES_PHOTO_TYPES) >= 1


def test_lewd_shores_photo_types_all_have_label_and_prompt(aig):
    for key, info in aig.LEWD_SHORES_PHOTO_TYPES.items():
        assert "label" in info
        assert "prompt_enhancement" in info


# ── SNAPSHOT_PHOTO_MODIFIERS ──────────────────────────────────────────────────

def test_snapshot_photo_modifiers_has_plain(aig):
    assert "plain" in aig.SNAPSHOT_PHOTO_MODIFIERS


def test_snapshot_photo_modifiers_keys_match_snapshot_types(aig):
    from modules.picture_widget import SNAPSHOT_TYPES
    for key in aig.SNAPSHOT_PHOTO_MODIFIERS:
        assert key in SNAPSHOT_TYPES, f"modifier key {key!r} not in SNAPSHOT_TYPES"


# ── LEWD_SHORES_PHOTO_MODIFIERS ───────────────────────────────────────────────

def test_lewd_shores_photo_modifiers_keys_match_lewd_types(aig):
    from modules.picture_widget import LEWD_TYPES
    for key in aig.LEWD_SHORES_PHOTO_MODIFIERS:
        assert key in LEWD_TYPES, f"modifier key {key!r} not in LEWD_TYPES"


# ── WIDGET_TYPES routing ──────────────────────────────────────────────────────

def test_widget_types_photos_entry(aig):
    assert aig.WIDGET_TYPES["photos"] is aig.PHOTO_TYPES


def test_widget_types_photos_lewdshores_entry(aig):
    assert aig.WIDGET_TYPES["photos_lewdshores"] is aig.LEWD_SHORES_PHOTO_TYPES


def test_widget_types_love_lens_entry(aig):
    assert aig.WIDGET_TYPES["love_lens"] is aig.LOVE_LENS_TYPES


def test_widget_types_events_entry(aig):
    assert aig.WIDGET_TYPES["events"] is aig.EVENT_TYPES


# ── PHOTO_MODIFIER_TYPES routing ──────────────────────────────────────────────

def test_photo_modifier_types_photos_entry(aig):
    assert aig.PHOTO_MODIFIER_TYPES["photos"] is aig.SNAPSHOT_PHOTO_MODIFIERS


def test_photo_modifier_types_lewdshores_entry(aig):
    assert aig.PHOTO_MODIFIER_TYPES["photos_lewdshores"] is aig.LEWD_SHORES_PHOTO_MODIFIERS


# ── AiImageGenDialog — form builds without error ──────────────────────────────

@pytest.fixture()
def dialog_photos(qtbot):
    from modules.ai_image_gen import AiImageGenDialog
    dlg = AiImageGenDialog(None, "photos", lambda d: None)
    qtbot.addWidget(dlg)
    return dlg


@pytest.fixture()
def dialog_lewdshores(qtbot):
    from modules.ai_image_gen import AiImageGenDialog
    dlg = AiImageGenDialog(None, "photos_lewdshores", lambda d: None)
    qtbot.addWidget(dlg)
    return dlg


def test_dialog_photos_modifier_combo_has_any(dialog_photos):
    assert dialog_photos._cmb_modifier is not None
    assert dialog_photos._cmb_modifier.itemData(0) == ""
    assert dialog_photos._cmb_modifier.itemText(0) == "(any)"


def test_dialog_photos_modifier_combo_count(dialog_photos, aig):
    # (any) + one entry per modifier
    expected = 1 + len(aig.SNAPSHOT_PHOTO_MODIFIERS)
    assert dialog_photos._cmb_modifier.count() == expected


def test_dialog_lewdshores_modifier_combo_count(dialog_lewdshores, aig):
    expected = 1 + len(aig.LEWD_SHORES_PHOTO_MODIFIERS)
    assert dialog_lewdshores._cmb_modifier.count() == expected


def test_dialog_events_has_no_modifier_combo(qtbot, aig):
    from modules.ai_image_gen import AiImageGenDialog
    dlg = AiImageGenDialog(None, "events", lambda d: None)
    qtbot.addWidget(dlg)
    assert dlg._cmb_modifier is None


# ── _save_to_temp ─────────────────────────────────────────────────────────────

def test_save_to_temp_writes_file(aig, tmp_path):
    path = aig._save_to_temp(b"\xff\xd8\xff", 0, "jpeg", str(tmp_path))
    assert path.startswith(str(tmp_path))
    with open(path, "rb") as fh:
        assert fh.read() == b"\xff\xd8\xff"


def test_save_to_temp_uses_system_temp_when_no_output_dir(aig, tmp_path, monkeypatch):
    import tempfile
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    path = aig._save_to_temp(b"data", 1)
    assert "snapshot_pack_creator_ai" in path
