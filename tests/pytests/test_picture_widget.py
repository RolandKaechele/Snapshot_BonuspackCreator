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


# ── get_rare_photo_warning ───────────────────────────────────────────────────

def test_rare_photo_warning_none_when_no_photos(pw_module):
    assert pw_module.get_rare_photo_warning({"photos": []}) is None


def test_rare_photo_warning_none_within_limit(pw_module):
    # 10 photos → limit = ceil(10/10) = 1; one "rare" photo is within limit.
    photos = [{"color": "rare"}] + [{"color": "white"}] * 9
    assert pw_module.get_rare_photo_warning({"photos": photos}) is None


def test_rare_photo_warning_triggers_when_over_limit(pw_module):
    # 10 photos → limit = 1; two "rare" photos exceed it.
    photos = [{"color": "rare"}, {"color": "rare"}] + [{"color": "white"}] * 8
    msg = pw_module.get_rare_photo_warning({"photos": photos})
    assert msg is not None
    assert "2 photo(s)" in msg
    assert "allows 1" in msg


def test_rare_photo_warning_ignores_non_rare_colors(pw_module):
    photos = [{"color": "pink"}] * 5
    assert pw_module.get_rare_photo_warning({"photos": photos}) is None


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


# ── Removal confirmation (delete / move / keep / cancel) ────────────────────

def _add_photo_with_file(widget, tmp_path, name="photo1.png"):
    image_path = tmp_path / name
    image_path.write_bytes(b"fake png")
    widget._add_image_paths([str(image_path)])
    return image_path


def test_remove_selected_deletes_file_on_delete_choice(widget, tmp_path, monkeypatch):
    image_path = _add_photo_with_file(widget, tmp_path)
    monkeypatch.setattr(
        "modules.picture_widget.show_file_removal_choice", lambda *a, **k: "delete"
    )
    widget._list.item(0).setSelected(True)
    widget._on_remove_selected()
    assert not image_path.exists()
    assert widget._pm.data["photos"] == []


def test_remove_selected_keeps_file_on_keep_choice(widget, tmp_path, monkeypatch):
    image_path = _add_photo_with_file(widget, tmp_path)
    monkeypatch.setattr(
        "modules.picture_widget.show_file_removal_choice", lambda *a, **k: "keep"
    )
    widget._list.item(0).setSelected(True)
    widget._on_remove_selected()
    assert image_path.exists()
    assert widget._pm.data["photos"] == []


def test_remove_selected_cancel_keeps_photo_entry(widget, tmp_path, monkeypatch):
    image_path = _add_photo_with_file(widget, tmp_path)
    monkeypatch.setattr(
        "modules.picture_widget.show_file_removal_choice", lambda *a, **k: "cancel"
    )
    widget._list.item(0).setSelected(True)
    widget._on_remove_selected()
    assert image_path.exists()
    assert len(widget._pm.data["photos"]) == 1


def test_remove_selected_no_dialog_when_file_missing(widget, monkeypatch):
    widget._pm.add_photo({
        "name": "ghost", "source": "", "position": "upskirt", "type": "plain",
        "color": "white", "overwrite_type": "", "overwrite_color": "", "thumbnail": False,
    })
    widget._rebuild_list()
    called = []
    monkeypatch.setattr(
        "modules.picture_widget.show_file_removal_choice",
        lambda *a, **k: called.append(1) or "delete",
    )
    widget._list.item(0).setSelected(True)
    widget._on_remove_selected()
    assert not called
    assert widget._pm.data["photos"] == []
