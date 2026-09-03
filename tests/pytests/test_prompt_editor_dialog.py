"""Tests for PromptEditorDialog — category tabs, game filtering, big-field editing."""

import json
import pytest


@pytest.fixture()
def sample_prompts_file(tmp_path):
    data = {
        "NEGATIVE_PROMPT": "global neg",
        "PHOTO_TYPES": {"upskirt": {"label": "Upskirt", "prompt_enhancement": "p1",
                                     "negative_prompt": "n1"}},
        "LOVE_LENS_TYPES": {"standing_nude": {"label": "Standing", "prompt_enhancement": "p2",
                                               "negative_prompt": ""}},
        "EVENT_TYPES": {"alley_night": {"label": "Alley", "prompt_enhancement": "p3",
                                         "negative_prompt": ""}},
        "LOVE_LENS_OVERLAY_TYPES": {"overlayStart": {"label": "Start", "prompt_enhancement": "p4",
                                                      "negative_prompt": ""}},
        "LEWD_SHORES_PHOTO_TYPES": {"beachFront": {"label": "Beach", "prompt_enhancement": "p5",
                                                    "negative_prompt": ""}},
        "SNAPSHOT_PHOTO_MODIFIERS": {"plain": {"label": "Plain", "prompt_enhancement": "p6",
                                                "negative_prompt": ""}},
        "LEWD_SHORES_PHOTO_MODIFIERS": {"front view": {"label": "Front", "prompt_enhancement": "p7",
                                                        "negative_prompt": ""}},
    }
    path = tmp_path / "prompts.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture()
def dialog(qtbot, sample_prompts_file, monkeypatch):
    import modules.ai_image_gen as aig
    monkeypatch.setattr(aig, "default_prompt_file", lambda: str(sample_prompts_file))
    from modules.prompt_editor_dialog import PromptEditorDialog
    dlg = PromptEditorDialog(None)
    qtbot.addWidget(dlg)
    return dlg


def test_tabs_are_sorted_alphabetically(dialog):
    titles = [dialog._tabs.tabText(i) for i in range(dialog._tabs.count())]
    assert titles == sorted(titles)


def test_loads_global_negative_prompt(dialog):
    assert dialog._edit_global_negative.text() == "global neg"


def test_table_populated_from_file(dialog):
    table = dialog._tables["PHOTO_TYPES"]
    assert table.rowCount() == 1
    assert table.item(0, 0).text() == "upskirt"
    assert table.item(0, 1).text() == "Upskirt"
    assert table.item(0, 2).text() == "p1"
    assert table.item(0, 3).text() == "n1"


def test_game_filter_all_shows_every_tab(dialog):
    dialog._cmb_game.setCurrentIndex(dialog._cmb_game.findData(""))
    for i in range(dialog._tabs.count()):
        assert dialog._tabs.isTabVisible(i)


def test_game_filter_lewdshores_hides_snapshot_only_tabs(dialog):
    dialog._cmb_game.setCurrentIndex(dialog._cmb_game.findData("lewdshores"))
    from modules.prompt_editor_dialog import _CATEGORY_KEYS
    for i, key in enumerate(_CATEGORY_KEYS):
        expected_visible = key in ("LEWD_SHORES_PHOTO_TYPES", "LEWD_SHORES_PHOTO_MODIFIERS")
        assert dialog._tabs.isTabVisible(i) == expected_visible


def test_game_filter_snapshot_hides_lewdshores_only_tabs(dialog):
    dialog._cmb_game.setCurrentIndex(dialog._cmb_game.findData("snapshot"))
    from modules.prompt_editor_dialog import _CATEGORY_KEYS
    for i, key in enumerate(_CATEGORY_KEYS):
        expected_visible = key not in ("LEWD_SHORES_PHOTO_TYPES", "LEWD_SHORES_PHOTO_MODIFIERS")
        assert dialog._tabs.isTabVisible(i) == expected_visible


def test_initial_game_preselects_combo(qtbot, sample_prompts_file, monkeypatch):
    import modules.ai_image_gen as aig
    monkeypatch.setattr(aig, "default_prompt_file", lambda: str(sample_prompts_file))
    from modules.prompt_editor_dialog import PromptEditorDialog
    dlg = PromptEditorDialog(None, initial_game="lewdshores")
    qtbot.addWidget(dlg)
    assert dlg._cmb_game.currentData() == "lewdshores"


def test_add_and_remove_row(dialog):
    table = dialog._tables["PHOTO_TYPES"]
    dialog._on_add_row("PHOTO_TYPES")
    assert table.rowCount() == 2
    table.selectRow(1)
    dialog._on_remove_row("PHOTO_TYPES")
    assert table.rowCount() == 1


def test_collect_all_round_trips_data(dialog):
    collected = dialog._collect_all()
    assert collected["NEGATIVE_PROMPT"] == "global neg"
    assert collected["PHOTO_TYPES"]["upskirt"]["prompt_enhancement"] == "p1"
    assert collected["PHOTO_TYPES"]["upskirt"]["negative_prompt"] == "n1"


def test_save_writes_file_and_reloads_prompts(dialog, sample_prompts_file, monkeypatch):
    import modules.prompt_editor_dialog as ped
    monkeypatch.setattr(ped, "show_info", lambda *a, **k: None)
    table = dialog._tables["PHOTO_TYPES"]
    table.item(0, 2).setText("changed prompt")
    dialog._save_to(str(sample_prompts_file))

    with open(sample_prompts_file, encoding="utf-8") as f:
        saved = json.load(f)
    assert saved["PHOTO_TYPES"]["upskirt"]["prompt_enhancement"] == "changed prompt"

    import modules.ai_image_gen as aig
    assert aig.PHOTO_TYPES["upskirt"]["prompt_enhancement"] == "changed prompt"


def test_edit_text_dialog_returns_new_text_on_accept(dialog, monkeypatch, qtbot):
    from PyQt6.QtWidgets import QDialog
    monkeypatch.setattr(QDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    result = dialog._edit_text_dialog("Title", "old text")
    assert result == "old text"


def test_edit_text_dialog_returns_none_on_cancel(dialog, monkeypatch):
    from PyQt6.QtWidgets import QDialog
    monkeypatch.setattr(QDialog, "exec", lambda self: QDialog.DialogCode.Rejected)
    result = dialog._edit_text_dialog("Title", "old text")
    assert result is None
