---
applyTo: "**"
---

## Coding Conventions

- Python 3.12 features are fine (`match`/`case`, `tomllib`, etc.).
- **PyQt6 only** — do not suggest PyQt5 or PySide6.
- Use `PyQt6.QtWidgets`, `PyQt6.QtGui`, `PyQt6.QtCore` — not the Qt5-style flat imports.
- In PyQt6, enum values are fully qualified: `Qt.AlignmentFlag.AlignCenter`, not `Qt.AlignCenter`.
- `QAction` lives in `PyQt6.QtGui`, not `PyQt6.QtWidgets`.
- No type annotations required unless explicitly asked.
- Modify only functions/classes directly required for the requested change.
- Each major feature lives in its own module under `src/modules/`.
- Stylesheet is loaded once from `src/ui/style.qss`; do not embed inline style strings in Python code.

## Debug Output (`src/app_debug.py`)

- Central debug flag module — import with `from app_debug import dlog as _dlog`.
- Call `_dlog("Tag.method", "message")` inside methods.
- `main.py` enables it via `set_debug(True)` when `--debug` is passed.
- Never use `print()` for debug output in production code paths.

## Dialogs (`src/ui/dialogs.py`)

- Never use `QMessageBox.warning`, `QMessageBox.critical`, or `QMessageBox.information` directly.
- Use the shared helpers instead: `show_info`, `show_warning`, `show_error` from `src/ui/dialogs.py`.
- All three accept `parent`, `title`, `message`, and an optional `tag` for `_dlog` output.
- `show_error` additionally accepts `exc: Exception | None` — pass the caught exception to include the traceback in debug mode.
- Import: `from ui.dialogs import show_info, show_warning, show_error`
- `QMessageBox.about` is the only acceptable direct `QMessageBox` use (About dialog).

## Plugin System (`src/modules/plugin_system.py`)

- Plugins are Python packages dropped into the `plugins/` directory.
- Each plugin must expose a `register(app)` function.
- The plugin loader discovers and imports them at startup; import errors are caught and logged, never fatal.
