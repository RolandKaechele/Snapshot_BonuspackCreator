"""Application entry point."""

import argparse
import sys
import os

# Resolve src/ directory for relative imports when launched from project root
sys.path.insert(0, os.path.dirname(__file__))

from app_debug import set_debug
from ui.main_window import MainWindow
from modules.ai_image_gen import reload_prompts
from PyQt6.QtWidgets import QApplication #type: ignore
from PyQt6.QtCore import Qt

# Required before QApplication is created so QtWebEngineWidgets can be imported later.
QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)


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
    if args.prompt:
        reload_prompts(args.prompt)

    app = QApplication(sys.argv)
    app.setApplicationName("Snapshot Pack Creator")
    app.setOrganizationName("Fileknot")

    qss_path = os.path.join(os.path.dirname(__file__), "ui", "style.qss")
    if os.path.exists(qss_path):
        with open(qss_path, encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
