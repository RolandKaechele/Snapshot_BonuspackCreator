"""QMainWindow shell — assembles all modules into one window."""

import os

from PyQt6.QtWidgets import ( #type: ignore
    QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QStatusBar,
)
from PyQt6.QtCore import Qt #type: ignore

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
from modules.orphaned_files import OrphanedFilesWidget
from modules.plugin_system import PluginSystem


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Snapshot Pack Creator")
        self.resize(1200, 800)

        self._pack_manager = PackManager()
        self._import_export = ImportExportManager(self)
        self._plugin_system = PluginSystem(self)

        self._build_ui()
        build_menubar(self)
        self._statusbar_ctrl = StatusbarController(self.statusBar())
        self._plugin_system.load_plugins()

        self._statusbar_ctrl.set_info("Ready. Open or create a pack to begin.")
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
        self._orphaned_widget = OrphanedFilesWidget(self._pack_manager)

        self._tabs.addTab(self._pack_info_widget, "Pack Info")
        self._tabs.addTab(self._picture_widget, "Photos")
        self._tabs.addTab(self._overwrite_texts, "Overwrite Texts")
        self._tabs.addTab(self._event_widget, "City Events")    # index 3
        self._tabs.addTab(self._cutscene_widget, "Cutscenes")   # index 4 — hidden until game supports it
        self._tabs.addTab(self._love_lens_widget, "Love Lens")  # index 5
        self._tabs.addTab(self._orphaned_widget, "Orphaned Files")  # index 6 — shown only when needed
        self._tabs.setTabVisible(4, False)
        self._tabs.setTabVisible(6, False)

        self._pack_info_widget.game_changed.connect(self._on_game_changed)
        self.setCentralWidget(self._tabs)

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
            self._statusbar_ctrl.set_ok(f"Saved: {os.path.basename(path)}")
        except Exception as exc:
            show_error(self, "Save Failed", str(exc), exc=exc,
                       tag="MainWindow.on_save_pack_as")
            self._statusbar_ctrl.set_error(f"Save failed: {exc}")

    def on_import_bonus_content(self) -> None:
        self._import_export.run_import()

    def on_export_bonus_content(self) -> None:
        self._import_export.run_export()

    # ── Edit menu handlers ──────────────────────────────────────────────────

    def on_settings(self) -> None:
        show_info(self, "Settings", "No settings yet.", tag="MainWindow.on_settings")

    # ── Tools menu handlers ─────────────────────────────────────────

    def on_manage_plugins(self) -> None:
        info = "\n".join(self._plugin_system.loaded_plugin_names()) or "No plugins loaded."
        show_info(self, "Loaded Plugins", info, tag="MainWindow.on_manage_plugins")

    # ── Help menu handlers ──────────────────────────────────────────────────

    def on_about(self) -> None:
        show_info(
            self,
            "About Snapshot Pack Creator",
            f"Snapshot Pack Creator  {BUILD_VERSION}\n"
            "Creates bonus content packs for Snapshot! and Snapshot: Lewd Shores.\n\n"
            "Built with Python 3.12 + PyQt6.",
            tag="MainWindow.on_about",
        )

    # ── Internal ────────────────────────────────────────────────────────────

    def _on_game_changed(self, game: str) -> None:
        snapshot_only = game == "snapshot"
        for idx in (3, 5):  # City Events, Love Lens (Cutscenes index 4 stays hidden)
            self._tabs.setTabVisible(idx, snapshot_only)

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
        """Refresh the orphaned-files tab and show/hide it based on content."""
        folder = self._pack_manager.get("source_folder", "")
        self._orphaned_widget.refresh(folder)
        has_content = (self._orphaned_widget._list_orphaned.count() > 0
                       or self._orphaned_widget._list_broken.count() > 0)
        self._tabs.setTabVisible(6, has_content)

    def status(self) -> StatusbarController:
        return self._statusbar_ctrl
