"""Menubar builder — attaches actions to QMainWindow."""

from PyQt6.QtGui import QAction #type: ignore
from PyQt6.QtWidgets import QMenuBar, QMainWindow #type: ignore

from app_debug import dlog as _dlog


def build_menubar(window: QMainWindow) -> None:
    """Populate *window*'s menu bar with all application menus."""
    bar: QMenuBar = window.menuBar()

    # File
    file_menu = bar.addMenu("&File")

    act_new = QAction("&New Pack", window)
    act_new.setShortcut("Ctrl+N")
    act_new.triggered.connect(window.on_new_pack)
    file_menu.addAction(act_new)

    act_open = QAction("&Open Pack…", window)
    act_open.setShortcut("Ctrl+O")
    act_open.triggered.connect(window.on_open_pack)
    file_menu.addAction(act_open)

    act_save = QAction("&Save Pack", window)
    act_save.setShortcut("Ctrl+S")
    act_save.triggered.connect(window.on_save_pack)
    file_menu.addAction(act_save)

    act_save_as = QAction("Save Pack &As…", window)
    act_save_as.setShortcut("Ctrl+Shift+S")
    act_save_as.triggered.connect(window.on_save_pack_as)
    file_menu.addAction(act_save_as)

    file_menu.addSeparator()

    act_import = QAction("&Import Bonus Content…", window)
    act_import.triggered.connect(window.on_import_bonus_content)
    file_menu.addAction(act_import)

    act_export = QAction("&Export Bonus Content…", window)
    act_export.triggered.connect(window.on_export_bonus_content)
    file_menu.addAction(act_export)

    file_menu.addSeparator()

    act_quit = QAction("&Quit", window)
    act_quit.setShortcut("Ctrl+Q")
    act_quit.triggered.connect(window.close)
    file_menu.addAction(act_quit)

    # Edit
    edit_menu = bar.addMenu("&Edit")

    act_settings = QAction("&Settings…", window)
    act_settings.triggered.connect(window.on_settings)
    edit_menu.addAction(act_settings)

    # Tools
    tools_menu = bar.addMenu("&Tools")

    act_plugins = QAction("&Manage Plugins…", window)
    act_plugins.triggered.connect(window.on_manage_plugins)
    tools_menu.addAction(act_plugins)

    # Help
    help_menu = bar.addMenu("&Help")

    act_about = QAction("&About…", window)
    act_about.triggered.connect(window.on_about)
    help_menu.addAction(act_about)

    _dlog("menubar.build_menubar", "Menubar built")
