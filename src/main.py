"""Application entry point."""

import sys
import os

# Resolve src/ directory for relative imports when launched from project root
sys.path.insert(0, os.path.dirname(__file__))

from app_debug import set_debug
from ui.main_window import MainWindow
from PyQt6.QtWidgets import QApplication #type: ignore
from PyQt6.QtCore import Qt

# Required before QApplication is created so QtWebEngineWidgets can be imported later.
QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)


def main() -> None:
    if "--debug" in sys.argv or "-v" in sys.argv:
        set_debug(True)

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
