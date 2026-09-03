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
