"""Application entry point."""

import argparse
import subprocess
import sys
import os

# Resolve src/ directory for relative imports when launched from project root
sys.path.insert(0, os.path.dirname(__file__))

from app_debug import set_debug, enable_file_logging, dlog
from ui.main_window import MainWindow
from ui.torch_install_dialog import TorchInstallDialog
from ui.plugin_deps_install_dialog import PluginDepsInstallDialog
from modules.ai_image_gen import reload_prompts
from modules import torch_installer, plugin_deps
from PyQt6.QtWidgets import QApplication #type: ignore
from PyQt6.QtCore import Qt

# Required before QApplication is created so QtWebEngineWidgets can be imported later.
QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)


def _restart_app() -> None:
    """Relaunch the app in a fresh process and exit this one.

    Packages pip-installed into _internal/ mid-process (torch, plugin deps)
    aren't reliably importable afterwards even with importlib.invalidate_caches()
    -- native extensions/DLL search paths and C-level state are only set up
    once per process. A fresh process guarantees a clean import of everything
    just installed.
    """
    dlog("main", "restarting app after dependency install")
    if torch_installer.is_frozen():
        cmd = [sys.executable] + sys.argv[1:]
    else:
        cmd = [sys.executable] + sys.argv
    subprocess.Popen(cmd)
    sys.exit(0)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="Snapshot Pack Creator",
        description="Windows desktop app for creating/editing Snapshot! and Lewd Shores bonus packs.",
    )
    parser.add_argument("--debug", "-v", action="store_true", help="Enable debug logging")
    parser.add_argument("--prompt", default=None, help="Path to a custom prompts JSON file")
    args, _ = parser.parse_known_args(sys.argv[1:])

    if args.debug:
        set_debug(True)
        log_path = enable_file_logging()
        dlog("main", f"debug log file: {log_path}")
    if args.prompt:
        reload_prompts(args.prompt)

    app = QApplication(sys.argv)
    app.setApplicationName("Snapshot Pack Creator")
    app.setOrganizationName("Fileknot")

    qss_path = os.path.join(os.path.dirname(__file__), "ui", "style.qss")
    if os.path.exists(qss_path):
        with open(qss_path, encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    if torch_installer.is_frozen() and not torch_installer.is_torch_installed():
        torch_dlg = TorchInstallDialog()
        torch_dlg.exec()
        if torch_dlg.success:
            _restart_app()
    torch_installer.ensure_stdlib_complete()

    missing_plugin_deps = plugin_deps.missing_requirements()
    if missing_plugin_deps:
        deps_dlg = PluginDepsInstallDialog(missing_plugin_deps)
        deps_dlg.exec()
        if deps_dlg.success:
            _restart_app()

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
