"""Tests for PackInfoWidget color swatch rendering (background-color box, not glyph)."""

import pytest


@pytest.fixture()
def widget(qtbot):
    from modules.pack_manager import PackManager
    from modules.pack_info_widget import PackInfoWidget
    pm = PackManager()
    pm.new_pack()
    w = PackInfoWidget(pm)
    qtbot.addWidget(w)
    return w


def test_badge_color_swatch_has_no_glyph_text(widget):
    # Regression: swatch used to be a QLabel("⬛") tinted via CSS "color",
    # which rendered as a hollow box. It must now be an empty-text box
    # painted via "background-color".
    assert widget._lbl_color_swatch.text() == ""


def test_badge_color_swatch_fixed_square_size(widget):
    size = widget._lbl_color_swatch.size()
    assert size.width() == 22
    assert size.height() == 22


def test_badge_color_swatch_updates_background_on_valid_hex(widget):
    widget._edit_cat_color.setText("#ff0000")
    style = widget._lbl_color_swatch.styleSheet()
    assert "background-color: #ff0000" in style


def test_badge_color_swatch_no_background_on_invalid_hex(widget):
    widget._edit_cat_color.setText("not-a-color")
    style = widget._lbl_color_swatch.styleSheet()
    assert "background-color" not in style


def test_theme_color_swatch_has_no_glyph_text(widget):
    assert widget._lbl_theme_color_swatch.text() == ""


def test_theme_color_swatch_updates_background_on_valid_hex(widget):
    widget._edit_def_theme_color.setText("#00ff00")
    style = widget._lbl_theme_color_swatch.styleSheet()
    assert "background-color: #00ff00" in style


# ── Naughty Nightmares game support ───────────────────────────────────────

def test_game_combo_has_naughty_nightmares_option(widget):
    items = [widget._cmb_game.itemText(i) for i in range(widget._cmb_game.count())]
    assert items == ["Snapshot!", "Lewd Shores", "Naughty Nightmares"]


def test_selecting_naughty_nightmares_restricts_pack_type_to_photos(widget):
    widget._cmb_game.setCurrentIndex(2)  # Naughty Nightmares
    assert widget._pm.get("game") == "naughtynightmares"
    items = [widget._cmb_type.itemText(i) for i in range(widget._cmb_type.count())]
    assert items == ["Photos"]
    assert widget._pm.get("pack_type") == "photos"
    assert not widget._cmb_type.isEnabled()


def test_switching_away_from_naughty_nightmares_restores_pack_types(widget):
    widget._cmb_game.setCurrentIndex(2)  # Naughty Nightmares
    widget._cmb_game.setCurrentIndex(0)  # back to Snapshot!
    items = [widget._cmb_type.itemText(i) for i in range(widget._cmb_type.count())]
    assert items == ["Photos", "Events", "Love Lens"]
    assert widget._cmb_type.isEnabled()


def test_naughty_nightmares_resets_non_photos_pack_type(widget):
    widget._cmb_type.setCurrentIndex(1)  # Events
    assert widget._pm.get("pack_type") == "events"
    widget._cmb_game.setCurrentIndex(2)  # Naughty Nightmares
    assert widget._pm.get("pack_type") == "photos"


def test_refresh_restricts_pack_type_for_loaded_naughty_nightmares_pack(widget):
    widget._pm.set("game", "naughtynightmares")
    widget._pm.set("pack_type", "events")  # simulate a stray/invalid stored value
    widget.refresh()
    assert widget._cmb_game.currentText() == "Naughty Nightmares"
    items = [widget._cmb_type.itemText(i) for i in range(widget._cmb_type.count())]
    assert items == ["Photos"]
    assert widget._pm.get("pack_type") == "photos"


# ── Category field visibility (shared by Snapshot!/Naughty Nightmares/Lewd Shores) ──

def test_category_field_visible_for_snapshot(widget):
    widget._cmb_game.setCurrentIndex(0)  # Snapshot!
    assert widget._form_defaults.isRowVisible(widget._edit_def_category)


def test_category_field_visible_for_naughty_nightmares(widget):
    widget._cmb_game.setCurrentIndex(2)  # Naughty Nightmares
    assert widget._form_defaults.isRowVisible(widget._edit_def_category)


def test_category_field_visible_for_lewdshores(widget):
    widget._cmb_game.setCurrentIndex(1)  # Lewd Shores
    assert widget._form_defaults.isRowVisible(widget._edit_def_category)


# ── Custom (non-predefined) Defaults Position/Type/Color tokens ─────────────

def test_defaults_position_combo_is_editable(widget):
    assert widget._cmb_def_pos.isEditable()


def test_defaults_type_combo_is_editable(widget):
    assert widget._cmb_def_type.isEditable()


def test_defaults_color_combo_is_editable(widget):
    assert widget._cmb_def_color.isEditable()


def test_refresh_shows_custom_defaults_position_verbatim(widget):
    widget._pm.set("defaults_position", "ghostHands")
    widget.refresh()
    assert widget._cmb_def_pos.currentText() == "ghostHands"


def test_typing_custom_defaults_position_persists(widget):
    widget._cmb_def_pos.setCurrentText("demon")
    assert widget._pm.get("defaults_position") == "demon"

