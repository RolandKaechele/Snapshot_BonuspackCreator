"""Tests for PictureWidget constants and multi-selection / display-size behaviour."""

import pytest

# ── Constants (require Qt to be initialised so the module can be imported) ──

@pytest.fixture(scope="module")
def pw_module(qapp):  # noqa: ARG001
    from modules import picture_widget as pw
    return pw


def test_snapshot_positions_has_photo_booth(pw_module):
    values = [v for v, _ in pw_module.SNAPSHOT_POSITIONS]
    assert "photoBooth" in values


def test_snapshot_positions_photo_booth_label(pw_module):
    labels = {v: lbl for v, lbl in pw_module.SNAPSHOT_POSITIONS}
    assert labels["photoBooth"] == "Photo Booth"


def test_snapshot_positions_xbar_label(pw_module):
    labels = {v: lbl for v, lbl in pw_module.SNAPSHOT_POSITIONS}
    assert labels["xBar"] == "X-Ray Bar Photo (X-Ray Barstool)"


def test_snapshot_positions_flasher_label(pw_module):
    labels = {v: lbl for v, lbl in pw_module.SNAPSHOT_POSITIONS}
    assert labels["flasher"] == "Flasher (Yoruko Task)"


def test_snapshot_positions_window_label(pw_module):
    labels = {v: lbl for v, lbl in pw_module.SNAPSHOT_POSITIONS}
    assert labels["window"] == "Window (Yoruko Task)"


def test_display_sizes_has_three_entries(pw_module):
    assert len(pw_module._DISPLAY_SIZES) == 3


def test_display_sizes_labels(pw_module):
    labels = [lbl for lbl, _ in pw_module._DISPLAY_SIZES]
    assert labels == ["Standard", "Large", "Very Large"]


def test_display_sizes_pixels_ascending(pw_module):
    pixels = [px for _, px in pw_module._DISPLAY_SIZES]
    assert pixels == sorted(pixels)


# ── Widget behaviour ─────────────────────────────────────────────────────────

@pytest.fixture()
def widget(qtbot):
    from modules.pack_manager import PackManager
    from modules.picture_widget import PictureWidget
    pm = PackManager()
    pm.new_pack()
    w = PictureWidget(pm)
    qtbot.addWidget(w)
    w.show()
    return w


def test_widget_starts_with_empty_list(widget):
    assert widget._list.count() == 0


def test_widget_list_has_extended_selection(widget):
    from PyQt6.QtWidgets import QAbstractItemView
    assert widget._list.selectionMode() == QAbstractItemView.SelectionMode.ExtendedSelection


def test_display_size_combobox_has_three_items(widget):
    assert widget._cmb_display_size.count() == 3


def test_display_size_default_is_standard(widget):
    assert widget._cmb_display_size.currentText() == "Standard"


def test_detail_panel_disabled_when_no_selection(widget):
    assert not widget._cmb_position.isEnabled()


def test_thumbnail_label_hidden_by_default(widget):
    assert not widget._lbl_multi.isVisible()
