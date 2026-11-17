"""Tests for modules.plugin_dialog — PluginManagerDialog."""

from unittest.mock import patch, MagicMock

from modules.plugin_dialog import PluginManagerDialog


def _make_dialog(qtbot, tmp_path):
    plugin_system = MagicMock()
    plugin_system.loaded_plugin_names.return_value = []
    plugin_system.discovered_plugin_names.return_value = []
    dlg = PluginManagerDialog(None, plugin_system)
    qtbot.addWidget(dlg)
    return dlg


def test_open_plugins_folder_creates_dir_and_starts_file(qtbot, tmp_path):
    dlg = _make_dialog(qtbot, tmp_path)
    folder = str(tmp_path / "plugins")
    with patch("modules.plugin_dialog.plugins_dir", return_value=folder), \
         patch("os.startfile") as mock_startfile:
        dlg._on_open_plugins_folder()
    assert mock_startfile.called
    assert mock_startfile.call_args[0][0] == folder


def test_open_plugins_folder_shows_error_on_failure(qtbot, tmp_path):
    dlg = _make_dialog(qtbot, tmp_path)
    folder = str(tmp_path / "plugins")
    with patch("modules.plugin_dialog.plugins_dir", return_value=folder), \
         patch("os.startfile", side_effect=OSError("boom")), \
         patch("modules.plugin_dialog.show_error") as mock_show_error:
        dlg._on_open_plugins_folder()
    assert mock_show_error.called
