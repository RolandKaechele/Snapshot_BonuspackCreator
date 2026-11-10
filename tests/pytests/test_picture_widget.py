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


# ── Rare photo cap warning icon ──────────────────────────────────────────────

def test_rebuild_list_marks_excess_rare_photos_with_warning_icon(widget):
    widget._pm.set("game", "snapshot")
    widget._pm.set("pack_type", "photos")
    widget._pm.data["photos"] = [
        {"name": f"p{i}", "color": "rare" if i < 2 else "white"} for i in range(10)
    ]
    widget._rebuild_list()
    texts = [widget._list.item(i).text() for i in range(widget._list.count())]
    assert texts[0].startswith("\u26a0")
    assert texts[1].startswith("\u26a0")
    assert not texts[2].startswith("\u26a0")


def test_rebuild_list_no_warning_icon_when_rare_within_limit(widget):
    widget._pm.set("game", "snapshot")
    widget._pm.set("pack_type", "photos")
    widget._pm.data["photos"] = [
        {"name": f"p{i}", "color": "rare" if i == 0 else "white"} for i in range(10)
    ]
    widget._rebuild_list()
    texts = [widget._list.item(i).text() for i in range(widget._list.count())]
    assert not any(t.startswith("\u26a0") for t in texts)


def test_rebuild_list_tooltip_includes_issue_flag_note(widget):
    widget._pm.set("game", "snapshot")
    widget._pm.set("pack_type", "photos")
    widget._pm.data["photos"] = [
        {"name": "p0", "color": "white", "issue_flag": True, "issue_note": "wrong angle"},
    ]
    widget._rebuild_list()
    assert "wrong angle" in widget._list.item(0).toolTip()


def test_rebuild_list_tooltip_combines_all_applicable_warnings(widget):
    widget._pm.set("game", "snapshot")
    widget._pm.set("pack_type", "photos")
    widget._pm.data["photos"] = [
        {
            "name": "p0", "color": "rare", "position": "hypno",
            "issue_flag": True, "issue_note": "wrong angle",
        },
        {"name": "p1", "color": "rare"},
    ] + [{"name": f"p{i}", "color": "white"} for i in range(2, 10)]
    widget._rebuild_list()
    tooltip = widget._list.item(0).toolTip()
    assert "wrong angle" in tooltip
    assert "reserved for Pack Type" in tooltip
    assert "excess ones" in tooltip


# ── Rare photo cap confirmation on trait change ──────────────────────────────

def test_confirm_rare_cap_true_when_within_limit(widget):
    photos = [{"name": f"p{i}", "color": "white"} for i in range(10)]
    widget._pm.set("game", "snapshot")
    widget._pm.set("pack_type", "photos")
    assert widget._confirm_rare_cap([0], photos) is True


def test_confirm_rare_cap_prompts_when_over_limit(widget, monkeypatch):
    photos = [{"name": f"p{i}", "color": "white"} for i in range(10)]
    photos[0]["color"] = "rare"  # 1 already rare; limit = ceil(10/10) = 1
    widget._pm.set("game", "snapshot")
    widget._pm.set("pack_type", "photos")
    captured = {}

    def _fake_confirm(*a, **kw):
        captured["called"] = True
        return False

    monkeypatch.setattr("modules.picture_widget.show_confirm", _fake_confirm)
    assert widget._confirm_rare_cap([1], photos) is False
    assert captured.get("called")


def test_confirm_rare_cap_skipped_for_lewdshores(widget):
    photos = [{"name": f"p{i}", "color": "rare"} for i in range(10)]
    widget._pm.set("game", "lewdshores")
    widget._pm.set("pack_type", "photos")
    assert widget._confirm_rare_cap([0], photos) is True


def test_setting_rare_over_limit_reverts_when_cancelled(widget, monkeypatch):
    widget._pm.set("game", "snapshot")
    widget._pm.set("pack_type", "photos")
    widget._pm.data["photos"] = [
        {"name": f"p{i}", "color": "white", "position": "upskirt"} for i in range(10)
    ]
    widget._pm.data["photos"][0]["color"] = "rare"  # already at the limit (1)
    widget._rebuild_list()
    widget._list.setCurrentRow(1)  # select the 2nd photo (currently "white")

    monkeypatch.setattr("modules.picture_widget.show_confirm", lambda *a, **kw: False)
    widget._cmb_color_special.setCurrentText("rare")

    assert widget._pm.data["photos"][1]["color"] == "white"
    assert widget._cmb_color_special.currentText() == "white"


def test_setting_rare_over_limit_applies_when_confirmed(widget, monkeypatch):
    widget._pm.set("game", "snapshot")
    widget._pm.set("pack_type", "photos")
    widget._pm.data["photos"] = [
        {"name": f"p{i}", "color": "white", "position": "upskirt"} for i in range(10)
    ]
    widget._pm.data["photos"][0]["color"] = "rare"
    widget._rebuild_list()
    widget._list.setCurrentRow(1)

    monkeypatch.setattr("modules.picture_widget.show_confirm", lambda *a, **kw: True)
    widget._cmb_color_special.setCurrentText("rare")

    assert widget._pm.data["photos"][1]["color"] == "rare"


# ── AI Generate widget_type routing per game ─────────────────────────────────

def test_ai_generate_uses_photos_widget_type_for_snapshot(widget, monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "modules.picture_widget.open_ai_generate_dialog",
        lambda parent, wtype, *a, **k: captured.setdefault("wtype", wtype),
    )
    widget._pm.set("game", "snapshot")
    widget._on_ai_generate()
    assert captured["wtype"] == "photos"


def test_ai_generate_uses_lewdshores_widget_type(widget, monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "modules.picture_widget.open_ai_generate_dialog",
        lambda parent, wtype, *a, **k: captured.setdefault("wtype", wtype),
    )
    widget._pm.set("game", "lewdshores")
    widget._on_ai_generate()
    assert captured["wtype"] == "photos_lewdshores"


def test_ai_generate_uses_naughtynightmares_widget_type(widget, monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "modules.picture_widget.open_ai_generate_dialog",
        lambda parent, wtype, *a, **k: captured.setdefault("wtype", wtype),
    )
    widget._pm.set("game", "naughtynightmares")
    widget._on_ai_generate()
    assert captured["wtype"] == "photos_naughtynightmares"


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


# ── Custom (non-predefined) Position/Type/Color tokens ──────────────────────
# e.g. Naughty Nightmares [Special Traits] alias tokens like "ghostHands" that
# aren't in SNAPSHOT_POSITIONS/SNAPSHOT_TYPES/SNAPSHOT_COLORS.

def _add_custom_photo(widget):
    widget._pm.add_photo({
        "name": "monstercockattack1", "source": "",
        "position": "ghostHands", "type": "monster-cock-attack", "color": "teasing",
        "overwrite_type": "", "overwrite_color": "", "thumbnail": False,
    })
    widget._rebuild_list()
    widget._list.item(0).setSelected(True)


def test_position_combo_is_editable(widget):
    assert widget._cmb_position.isEditable()


def test_type_combo_is_editable(widget):
    assert widget._cmb_type.isEditable()


def test_color_combo_is_editable(widget):
    assert widget._cmb_color_special.isEditable()


def test_custom_position_token_displayed_verbatim(widget):
    _add_custom_photo(widget)
    assert widget._cmb_position.currentText() == "ghostHands"


def test_custom_type_token_displayed_verbatim(widget):
    _add_custom_photo(widget)
    assert widget._cmb_type.currentText() == "monster-cock-attack"


def test_custom_color_token_displayed_verbatim(widget):
    _add_custom_photo(widget)
    assert widget._cmb_color_special.currentText() == "teasing"


def test_custom_position_token_not_corrupted_by_other_combo_edits(widget):
    """Regression: touching Type/Color must not silently reset Position to index 0."""
    _add_custom_photo(widget)
    widget._cmb_type.setCurrentText("plain")
    assert widget._pm.data["photos"][0]["position"] == "ghostHands"


def test_typing_custom_position_persists_to_photo_data(widget):
    widget._pm.add_photo({
        "name": "p1", "source": "", "position": "upskirt", "type": "plain",
        "color": "white", "overwrite_type": "", "overwrite_color": "", "thumbnail": False,
    })
    widget._rebuild_list()
    widget._list.item(0).setSelected(True)
    widget._cmb_position.setCurrentText("demon")
    assert widget._pm.data["photos"][0]["position"] == "demon"
