"""Plugin system — discovers and loads Python plugin packages from plugins/."""

import os
import sys
import importlib
from typing import TYPE_CHECKING

from app_debug import dlog as _dlog

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QMainWindow #type: ignore

_PLUGINS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "plugins"
)


class PluginSystem:
    """Discovers and loads plugin packages from the plugins/ directory."""

    def __init__(self, app: "QMainWindow") -> None:
        self._app = app
        self._loaded: list[str] = []

    def load_plugins(self) -> None:
        plugins_dir = os.path.normpath(_PLUGINS_DIR)
        if not os.path.isdir(plugins_dir):
            _dlog("PluginSystem.load_plugins", f"plugins/ not found at {plugins_dir}")
            return

        if plugins_dir not in sys.path:
            sys.path.insert(0, plugins_dir)

        for entry in os.listdir(plugins_dir):
            entry_path = os.path.join(plugins_dir, entry)
            # Support both package dirs (with __init__.py) and plain .py modules
            is_package = os.path.isdir(entry_path) and os.path.exists(
                os.path.join(entry_path, "__init__.py")
            )
            is_module = entry.endswith(".py") and not entry.startswith("_")
            module_name = entry if is_package else (entry[:-3] if is_module else None)

            if not module_name:
                continue

            try:
                mod = importlib.import_module(module_name)
                if hasattr(mod, "register") and callable(mod.register):
                    mod.register(self._app)
                    self._loaded.append(module_name)
                    _dlog("PluginSystem.load_plugins", f"Loaded plugin: {module_name}")
                else:
                    _dlog("PluginSystem.load_plugins",
                          f"Plugin {module_name} has no register() — skipped")
            except Exception as exc:
                _dlog("PluginSystem.load_plugins",
                      f"Failed to load plugin {module_name}: {exc}")

    def loaded_plugin_names(self) -> list[str]:
        return list(self._loaded)
