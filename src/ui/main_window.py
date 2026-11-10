"""QMainWindow shell — assembles all modules into one window."""

import os

from PyQt6.QtWidgets import ( #type: ignore
    QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QStatusBar,
)
from PyQt6.QtCore import Qt, QTimer #type: ignore

from app_debug import dlog as _dlog
from ui.menubar import build_menubar
from ui.statusbar import StatusbarController
from ui.dialogs import show_info, show_warning, show_error
from modules.pack_manager import PackManager
from _version import BUILD_VERSION
from modules.import_export import ImportExportManager
from modules.pack_info_widget import PackInfoWidget
from modules.picture_widget import PictureWidget
from modules.overwrite_texts import OverwriteTextsWidget
from modules.event_widget import EventWidget
from modules.cutscene_widget import CutsceneWidget
from modules.love_lens import LoveLensWidget
from modules.warnings_tab import WarningsTabWidget
from modules.plugin_system import PluginSystem
from modules.ai_image_gen import get_torch_info
from modules.recent_files import load_recent, add_recent


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.resize(1200, 800)

        self._pack_manager = PackManager()
        self._import_export = ImportExportManager(self)
        self._plugin_system = PluginSystem(self)

        self._build_ui()
        build_menubar(self)
        self._statusbar_ctrl = StatusbarController(self.statusBar())
        self._plugin_system.load_plugins()

        for _w in (self._picture_widget, self._love_lens_widget, self._event_widget):
            if hasattr(_w, "update_ai_availability"):
                _w.update_ai_availability()

        torch_info = get_torch_info()
        _dlog("MainWindow.__init__", f"torch info: {torch_info or 'torch not installed'}")
        title = f"Snapshot Pack Creator  [{torch_info}]" if torch_info else "Snapshot Pack Creator"
        self.setWindowTitle(title)

        self._statusbar_ctrl.set_info("Ready. Open or create a pack to begin.")

        # Periodic undo/redo snapshot — coalesces rapid edits into one history step
        # since many widgets mutate nested pack data without going through mark_dirty().
        self._history_timer = QTimer(self)
        self._history_timer.setInterval(800)
        self._history_timer.timeout.connect(self._pack_manager.push_history)
        self._history_timer.start()

        _dlog("MainWindow.__init__", "Window ready")

    def _build_ui(self) -> None:
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)

        self._pack_info_widget = PackInfoWidget(self._pack_manager)
        self._picture_widget = PictureWidget(self._pack_manager)
        self._overwrite_texts = OverwriteTextsWidget(self._pack_manager)
        self._event_widget = EventWidget(self._pack_manager)
        self._cutscene_widget = CutsceneWidget(self._pack_manager)
        self._love_lens_widget = LoveLensWidget(self._pack_manager)
        self._orphaned_widget = WarningsTabWidget(self._pack_manager)

        self._tabs.addTab(self._pack_info_widget, "Pack Info")
        self._tabs.addTab(self._picture_widget, "Photos")
        self._tabs.addTab(self._overwrite_texts, "Overwrite Texts")
        self._tabs.addTab(self._event_widget, "City Events")    # index 3
        self._tabs.addTab(self._cutscene_widget, "Cutscenes")   # index 4 — hidden until game supports it
        self._tabs.addTab(self._love_lens_widget, "Love Lens")  # index 5
        self._tabs.addTab(self._orphaned_widget, "Warnings")  # index 6 — shown only when needed
        self._tabs.setTabVisible(4, False)
        self._tabs.setTabVisible(6, False)

        self._pack_info_widget.game_changed.connect(self._on_game_changed)
        self._event_widget.photos_changed.connect(self._picture_widget.refresh)
        self.setCentralWidget(self._tabs)
        self._on_game_changed(self._pack_manager.get("game", "snapshot"))

    # ── File menu handlers ──────────────────────────────────────────────────

    def on_new_pack(self) -> None:
        from ui.dialogs import show_confirm #type: ignore
        _dlog("MainWindow.on_new_pack", "New pack requested")
        if self._pack_manager.is_dirty:
            if not show_confirm(self, "New Pack",
                               "This will clear the current pack. Continue?",
                               tag="MainWindow.on_new_pack"):
                return
        self._pack_manager.new_pack()
        self._refresh_all()
        self._statusbar_ctrl.set_ok("New pack created.")

    def on_open_pack(self) -> None:
        from PyQt6.QtWidgets import QFileDialog #type: ignore
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Pack", "", "Pack JSON (*.json);;All files (*)"
        )
        if not path:
            return
        try:
            self._pack_manager.load(path)
            self._refresh_all()
            add_recent(path)
            self._statusbar_ctrl.set_ok(f"Loaded: {os.path.basename(path)}")
            _dlog("MainWindow.on_open_pack", f"Loaded {path}")
        except Exception as exc:
            show_error(self, "Open Failed", str(exc), exc=exc,
                       tag="MainWindow.on_open_pack")
            self._statusbar_ctrl.set_error(f"Failed to load: {exc}")

    def on_save_pack(self) -> None:
        if not self._pack_manager.current_path:
            self.on_save_pack_as()
            return
        try:
            self._pack_manager.save(self._pack_manager.current_path)
            add_recent(self._pack_manager.current_path)
            self._statusbar_ctrl.set_ok("Pack saved.")
        except Exception as exc:
            show_error(self, "Save Failed", str(exc), exc=exc,
                       tag="MainWindow.on_save_pack")
            self._statusbar_ctrl.set_error(f"Save failed: {exc}")

    def on_save_pack_as(self) -> None:
        from PyQt6.QtWidgets import QFileDialog #type: ignore
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Pack As", "", "Pack JSON (*.json);;All files (*)"
        )
        if not path:
            return
        try:
            self._pack_manager.save(path)
            add_recent(path)
            self._statusbar_ctrl.set_ok(f"Saved: {os.path.basename(path)}")
        except Exception as exc:
            show_error(self, "Save Failed", str(exc), exc=exc,
                       tag="MainWindow.on_save_pack_as")
            self._statusbar_ctrl.set_error(f"Save failed: {exc}")

    def on_import_bonus_content(self) -> None:
        self._import_export.run_import()

    def on_import_bonus_content_from_archive(self) -> None:
        self._import_export.run_import_from_archive()

    def on_export_bonus_content(self) -> None:
        self._import_export.run_export()

    def on_export_bonus_content_zip(self) -> None:
        self._import_export.run_export(also_zip=True)

    # ── Recent files ─────────────────────────────────────────────────────

    def on_populate_recent_menu(self) -> None:
        self._recent_menu.clear()
        recents = load_recent()
        if not recents:
            self._recent_menu.addAction("(No recent packs)").setEnabled(False)
            return
        for path in recents:
            action = self._recent_menu.addAction(path)
            action.triggered.connect(lambda checked=False, p=path: self._on_open_recent(p))

    def _on_open_recent(self, path: str) -> None:
        if not os.path.exists(path):
            show_warning(self, "File Not Found", f"Pack file no longer exists:\n{path}",
                        tag="MainWindow._on_open_recent")
            return
        if self._pack_manager.is_dirty:
            from ui.dialogs import show_confirm #type: ignore
            if not show_confirm(self, "Open Recent Pack",
                               "This will clear the current pack. Continue?",
                               tag="MainWindow._on_open_recent"):
                return
        try:
            self._pack_manager.load(path)
            self._refresh_all()
            add_recent(path)
            self._statusbar_ctrl.set_ok(f"Loaded: {os.path.basename(path)}")
        except Exception as exc:
            show_error(self, "Open Failed", str(exc), exc=exc,
                       tag="MainWindow._on_open_recent")
            self._statusbar_ctrl.set_error(f"Failed to load: {exc}")

    # ── Backups ──────────────────────────────────────────────────────────

    def on_restore_backup(self) -> None:
        path = self._pack_manager.current_path
        if not path:
            show_info(self, "Restore Previous Version",
                      "Save the pack at least once before restoring a backup.",
                      tag="MainWindow.on_restore_backup")
            return
        backups = self._pack_manager.list_backups(path)
        if not backups:
            show_info(self, "Restore Previous Version", "No backups found for this pack yet.",
                      tag="MainWindow.on_restore_backup")
            return
        from PyQt6.QtWidgets import QInputDialog #type: ignore
        labels = [b["timestamp"].strftime("%Y-%m-%d %H:%M:%S") for b in backups]
        label, ok = QInputDialog.getItem(
            self, "Restore Previous Version", "Choose a backup to restore:", labels, 0, False)
        if not ok or not label:
            return
        backup = backups[labels.index(label)]
        from ui.dialogs import show_confirm #type: ignore
        if not show_confirm(self, "Restore Previous Version",
                           f"Restore the pack to the version from {label}?\n"
                           "Unsaved changes in the current pack will be lost.",
                           tag="MainWindow.on_restore_backup"):
            return
        try:
            self._pack_manager.restore_backup(backup["path"])
            self._refresh_all()
            self._statusbar_ctrl.set_ok(f"Restored backup from {label}")
        except Exception as exc:
            show_error(self, "Restore Failed", str(exc), exc=exc,
                       tag="MainWindow.on_restore_backup")

    # ── Undo / Redo ──────────────────────────────────────────────────────

    def on_undo(self) -> None:
        if self._pack_manager.undo():
            self._refresh_all()
            self._statusbar_ctrl.set_ok("Undo.")
        else:
            self._statusbar_ctrl.set_info("Nothing to undo.")

    def on_redo(self) -> None:
        if self._pack_manager.redo():
            self._refresh_all()
            self._statusbar_ctrl.set_ok("Redo.")
        else:
            self._statusbar_ctrl.set_info("Nothing to redo.")

    # ── Edit menu handlers ──────────────────────────────────────────────────

    def on_settings(self) -> None:
        show_info(self, "Settings", "No settings yet.", tag="MainWindow.on_settings")

    # ── Tools menu handlers ─────────────────────────────────────────

    def on_manage_plugins(self) -> None:
        from modules.plugin_dialog import PluginManagerDialog
        PluginManagerDialog(self, self._plugin_system).exec()

    def on_edit_prompts(self) -> None:
        from modules.prompt_editor_dialog import PromptEditorDialog
        game = self._pack_manager.get("game", "")
        PromptEditorDialog(self, initial_game=game).exec()

    # ── Analysis tools ───────────────────────────────────────────────────

    def on_find_duplicates(self) -> None:
        from modules.asset_dedup import find_duplicate_assets
        groups = find_duplicate_assets(self._pack_manager.data)
        if not groups:
            show_info(self, "Find Duplicate Assets", "No duplicate assets found in this pack.",
                      tag="MainWindow.on_find_duplicates")
            return
        lines = []
        for group in groups:
            lines.append("Duplicate group:")
            lines.extend(f"  \u2022 {label}  ({path})" for label, path in group)
            lines.append("")
        show_info(self, "Find Duplicate Assets", "\n".join(lines).strip(),
                  tag="MainWindow.on_find_duplicates")

    def on_compare_packs(self) -> None:
        from PyQt6.QtWidgets import QFileDialog #type: ignore
        path_a, _ = QFileDialog.getOpenFileName(self, "Select First Pack", "", "Pack JSON (*.json)")
        if not path_a:
            return
        path_b, _ = QFileDialog.getOpenFileName(self, "Select Second Pack", "", "Pack JSON (*.json)")
        if not path_b:
            return
        try:
            import json
            from modules.pack_diff import diff_packs
            with open(path_a, encoding="utf-8") as f:
                data_a = json.load(f)
            with open(path_b, encoding="utf-8") as f:
                data_b = json.load(f)
            report = diff_packs(data_a, data_b)
            show_info(self, "Compare Packs",
                      f"{os.path.basename(path_a)}  vs  {os.path.basename(path_b)}\n\n{report}",
                      tag="MainWindow.on_compare_packs")
        except Exception as exc:
            show_error(self, "Compare Packs Failed", str(exc), exc=exc,
                       tag="MainWindow.on_compare_packs")

    def on_pack_statistics(self) -> None:
        from modules.pack_stats import compute_stats, format_stats_report
        stats = compute_stats(self._pack_manager.data)
        show_info(self, "Pack Statistics", format_stats_report(stats),
                  tag="MainWindow.on_pack_statistics")

    def on_generate_issue_report(self) -> None:
        from PyQt6.QtWidgets import QFileDialog #type: ignore
        from modules.issue_report import write_issue_report
        pack_id = self._pack_manager.get("id") or "pack"
        path, _ = QFileDialog.getSaveFileName(
            self, "Generate Issue Report", f"{pack_id}_issue_report.md",
            "Markdown (*.md);;All files (*)"
        )
        if not path:
            return
        try:
            write_issue_report(self._pack_manager.data, path)
            show_info(self, "Generate Issue Report", f"Issue report written to:\n{path}",
                      tag="MainWindow.on_generate_issue_report")
        except Exception as exc:
            show_error(self, "Generate Issue Report Failed", str(exc), exc=exc,
                       tag="MainWindow.on_generate_issue_report")

    # ── Help menu handlers ──────────────────────────────────────────────────

    def on_about(self) -> None:
        show_info(
            self,
            "About Snapshot Pack Creator",
            f"Snapshot Pack Creator  {BUILD_VERSION}\n"
            "Creates bonus content packs for Snapshot!, Snapshot: Lewd Shores, and Snapshot! Naughty Nightmares.\n\n"
            "Built with Python 3.12 + PyQt6.\n\n"
            "This app is not officially associated with Snapshot! or Tiny Secret Games.",
            tag="MainWindow.on_about",
        )

    # ── Internal ────────────────────────────────────────────────────────────

    def _on_game_changed(self, game: str) -> None:
        snapshot_only = game in ("snapshot", "naughtynightmares")
        events_capable = game in ("snapshot", "naughtynightmares", "lewdshores")
        pack_type = self._pack_manager.get("pack_type", "photos")
        self._tabs.setTabText(3, "Beach Events" if game == "lewdshores" else "City Events")
        self._tabs.setTabVisible(3, events_capable and pack_type == "events")   # City/Beach Events
        self._tabs.setTabVisible(5, snapshot_only and pack_type == "lovelens")  # Love Lens

    def _refresh_all(self) -> None:
        self._pack_info_widget.refresh()
        self._picture_widget.refresh()
        self._overwrite_texts.refresh()
        self._event_widget.refresh()
        self._cutscene_widget.refresh()
        self._love_lens_widget.refresh()
        self._refresh_orphaned()
        # Sync tab visibility after data is refreshed
        self._on_game_changed(self._pack_manager.get("game", "snapshot"))

    def _refresh_orphaned(self) -> None:
        """Refresh the warnings tab and show/hide it based on content."""
        folder = self._pack_manager.get("source_folder", "")
        self._orphaned_widget.refresh(folder)
        has_content = (self._orphaned_widget._list_warnings.count() > 0
                       or self._orphaned_widget._list_orphaned.count() > 0
                       or self._orphaned_widget._list_broken.count() > 0)
        self._tabs.setTabVisible(6, has_content)

    def status(self) -> StatusbarController:
        return self._statusbar_ctrl
