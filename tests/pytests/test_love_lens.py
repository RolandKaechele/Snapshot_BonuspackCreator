"""Tests for love_lens pre-export validation helpers."""

import pytest


@pytest.fixture(scope="module")
def ll_module(qapp):  # noqa: ARG001
    from modules import love_lens as ll
    return ll


def _complete_pack_data(ll_module):
    """Return pack_data with every required overlay/texture/photo slot filled."""
    return {
        "overlays": {key: ["a.png"] for key, _ in ll_module.OVERLAY_SLOTS},
        "textures": {
            slot[0]: ["a.png"] for slot in ll_module.TEXTURE_SLOTS
            if "(optional)" not in slot[1]
        },
        "love_lens_photos": {key: ["a.png"] for key, _ in ll_module.PHOTO_TYPES},
    }


# ── get_missing_love_lens_elements ──────────────────────────────────────────

def test_missing_elements_empty_when_all_filled(ll_module):
    assert ll_module.get_missing_love_lens_elements(_complete_pack_data(ll_module)) == []


def test_missing_elements_reports_empty_overlay_slot(ll_module):
    data = _complete_pack_data(ll_module)
    data["overlays"]["overlayStart"] = []
    missing = ll_module.get_missing_love_lens_elements(data)
    assert "Overlay – Start" in missing


def test_missing_elements_ignores_optional_texture_slot(ll_module):
    data = _complete_pack_data(ll_module)
    # droppedClothTexture is marked "(optional)" and is absent from the base fixture already.
    missing = ll_module.get_missing_love_lens_elements(data)
    assert not any("optional" in m for m in missing)


def test_missing_elements_reports_missing_photo_type(ll_module):
    data = _complete_pack_data(ll_module)
    data["love_lens_photos"]["standing_nude"] = []
    missing = ll_module.get_missing_love_lens_elements(data)
    assert "Photo – Standing nude" in missing


def test_missing_elements_handles_empty_pack_data(ll_module):
    missing = ll_module.get_missing_love_lens_elements({})
    required_texture_labels = [
        s[1] for s in ll_module.TEXTURE_SLOTS if "(optional)" not in s[1]
    ]
    assert len(missing) == (
        len(ll_module.OVERLAY_SLOTS) + len(required_texture_labels) + len(ll_module.PHOTO_TYPES)
    )


# ── get_duplicate_texture_files ─────────────────────────────────────────────

def test_duplicate_texture_files_none_when_unique(ll_module):
    data = {"textures": {"body": ["a.png"], "face": ["b.png"]}}
    assert ll_module.get_duplicate_texture_files(data) == []


def test_duplicate_texture_files_detects_shared_file(ll_module):
    data = {"textures": {"bodyBraTextures": ["shared.png"], "pantyTexture": ["shared.png"]}}
    duplicates = ll_module.get_duplicate_texture_files(data)
    assert len(duplicates) == 1
    assert "shared.png" in duplicates[0]
    assert "Body wearing bra" in duplicates[0]
    assert "Panty" in duplicates[0]


def test_duplicate_texture_files_ignores_repeat_within_same_slot(ll_module):
    # Same slot listing the same path twice is not a cross-slot duplicate concern here,
    # but the helper still flags any path seen under >1 slot entries total.
    data = {"textures": {"body": ["a.png"]}}
    assert ll_module.get_duplicate_texture_files(data) == []


def test_duplicate_texture_files_empty_pack_data(ll_module):
    assert ll_module.get_duplicate_texture_files({}) == []


# ── refresh() must not corrupt hairStyle/accessories mid-update ────────────
# Regression test: LoveLensWidget.refresh() used to read a live reference to
# pm.data["love_lens"], and each combo's currentIndexChanged→_save_character
# could clobber fields not yet applied before their own _set_combo ran.

def test_refresh_preserves_hairstyle_and_accessories(qtbot):
    from modules.pack_manager import PackManager
    from modules.love_lens import LoveLensWidget
    pm = PackManager()
    pm.new_pack()
    pm.data["love_lens"] = {
        "model": "slim", "hairStyle": "pigtails", "accessories": "elvenears",
    }
    widget = LoveLensWidget(pm)
    qtbot.addWidget(widget)
    widget.refresh()
    assert pm.data["love_lens"]["hairStyle"] == "pigtails"
    assert pm.data["love_lens"]["accessories"] == "elvenears"


def test_refresh_matches_accessories_label_with_space(qtbot):
    # "Elven Ears" (display label) must match the ini token "elvenears".
    from modules.pack_manager import PackManager
    from modules.love_lens import LoveLensWidget
    pm = PackManager()
    pm.new_pack()
    pm.data["love_lens"] = {"accessories": "elvenears"}
    widget = LoveLensWidget(pm)
    qtbot.addWidget(widget)
    widget.refresh()
    assert widget._cmb_accessories.currentText() == "Elven Ears"


# ── Hair/eye color swatches (background-color box, not glyph text) ────────
# Regression: swatch used to be a QLabel("⬛") tinted via CSS "color", which
# rendered as a hollow box regardless of the selected hex value.

def test_hair_color_swatch_has_no_glyph_text(qtbot):
    from modules.pack_manager import PackManager
    from modules.love_lens import LoveLensWidget
    from PyQt6.QtWidgets import QLabel
    pm = PackManager()
    pm.new_pack()
    widget = LoveLensWidget(pm)
    qtbot.addWidget(widget)
    swatch = widget._edit_hair_color.parentWidget().findChildren(QLabel)[0]
    assert swatch.text() == ""


def test_hair_color_swatch_updates_background_on_valid_hex(qtbot):
    from modules.pack_manager import PackManager
    from modules.love_lens import LoveLensWidget
    from PyQt6.QtWidgets import QLabel
    pm = PackManager()
    pm.new_pack()
    widget = LoveLensWidget(pm)
    qtbot.addWidget(widget)
    widget._edit_hair_color.setText("#fafafa")
    swatch = widget._edit_hair_color.parentWidget().findChildren(QLabel)[0]
    assert swatch.text() == ""
    assert "background-color: #fafafa" in swatch.styleSheet()

