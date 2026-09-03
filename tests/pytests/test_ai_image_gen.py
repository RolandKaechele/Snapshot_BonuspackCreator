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


# ── prompts.json loading / negative_prompt overrides ──────────────────────────

def test_negative_prompt_is_nonempty_string(aig):
    assert isinstance(aig.NEGATIVE_PROMPT, str)
    assert aig.NEGATIVE_PROMPT


def test_default_prompt_file_points_at_src_prompts_json(aig):
    path = aig.default_prompt_file()
    assert path.endswith("prompts.json")


@pytest.mark.parametrize("category", [
    "PHOTO_TYPES", "LOVE_LENS_TYPES", "EVENT_TYPES", "LOVE_LENS_OVERLAY_TYPES",
    "LEWD_SHORES_PHOTO_TYPES", "SNAPSHOT_PHOTO_MODIFIERS", "LEWD_SHORES_PHOTO_MODIFIERS",
])
def test_all_entries_have_negative_prompt_key(aig, category):
    entries = getattr(aig, category)
    for key, info in entries.items():
        assert "negative_prompt" in info, f"{category}[{key!r}] missing 'negative_prompt'"


def test_reload_prompts_overrides_in_place(aig, tmp_path):
    original = dict(aig.PHOTO_TYPES["upskirt"])
    custom_path = tmp_path / "custom_prompts.json"
    custom_path.write_text(
        '{"NEGATIVE_PROMPT": "custom neg", '
        '"PHOTO_TYPES": {"upskirt": {"label": "Custom", '
        '"prompt_enhancement": "custom prompt", "negative_prompt": "custom neg override"}}}',
        encoding="utf-8",
    )
    try:
        aig.reload_prompts(str(custom_path))
        assert aig.PHOTO_TYPES["upskirt"]["label"] == "Custom"
        assert aig.PHOTO_TYPES["upskirt"]["negative_prompt"] == "custom neg override"
        assert aig.NEGATIVE_PROMPT == "custom neg"
        # WIDGET_TYPES still references the same (mutated) dict object
        assert aig.WIDGET_TYPES["photos"] is aig.PHOTO_TYPES
    finally:
        # Restore defaults so later tests in this module see the original data
        aig.PHOTO_TYPES["upskirt"].clear()
        aig.PHOTO_TYPES["upskirt"].update(original)
        aig.reload_prompts()


def test_reload_prompts_ignores_missing_file(aig):
    before = dict(aig.PHOTO_TYPES["upskirt"])
    aig.reload_prompts("/nonexistent/path/prompts.json")
    assert aig.PHOTO_TYPES["upskirt"] == before


def test_dialog_events_has_no_modifier_combo(qtbot, aig):
    from modules.ai_image_gen import AiImageGenDialog
    dlg = AiImageGenDialog(None, "events", lambda d: None)
    qtbot.addWidget(dlg)
    assert dlg._cmb_modifier is None


# ── _save_to_temp / _VerifySessionDialog ──────────────────────────────────────
# Moved to plugins/perchance_diffusion/tests/test_perchance_diffusion.py — this
# behavior now lives in plugins/perchance_diffusion/__init__.py, and its tests
# travel with the plugin rather than the core app test suite.


