"""Plugin system — discovers and loads Python plugin packages from plugins/."""

import json
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

_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "plugin_config.json"
)


def load_disabled_plugins() -> set[str]:
    """Return the set of plugin module names the user has disabled."""
    path = os.path.normpath(_CONFIG_PATH)
    if not os.path.exists(path):
        return set()
    try:
        with open(path, encoding="utf-8") as f:
            return set(json.load(f).get("disabled", []))
    except (OSError, json.JSONDecodeError):
        return set()


def save_disabled_plugins(disabled: set[str]) -> None:
    path = os.path.normpath(_CONFIG_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"disabled": sorted(disabled)}, f, indent=2)


class PluginSystem:
    """Discovers and loads plugin packages from the plugins/ directory."""

    def __init__(self, app: "QMainWindow") -> None:
        self._app = app
        self._loaded: list[str] = []
        self._info: dict[str, dict] = {}
        self._discovered: list[str] = []

    def discovered_plugin_names(self) -> list[str]:
        """All plugin module names found in plugins/, loaded or not."""
        return list(self._discovered)

    def load_plugins(self) -> None:
        plugins_dir = os.path.normpath(_PLUGINS_DIR)
        if not os.path.isdir(plugins_dir):
            _dlog("PluginSystem.load_plugins", f"plugins/ not found at {plugins_dir}")
            return

        if plugins_dir not in sys.path:
            sys.path.insert(0, plugins_dir)

        disabled = load_disabled_plugins()

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

            self._discovered.append(module_name)
            if module_name in disabled:
                _dlog("PluginSystem.load_plugins", f"Skipped disabled plugin: {module_name}")
                continue

            try:
                mod = importlib.import_module(module_name)
                if hasattr(mod, "register") and callable(mod.register):
                    mod.register(self._app)
                    self._loaded.append(module_name)
                    self._info[module_name] = {
                        "version": getattr(mod, "__version__", ""),
                        "description": (getattr(mod, "__doc__", "") or "").strip().splitlines()[0]
                        if getattr(mod, "__doc__", "") else "",
                    }
                    _dlog("PluginSystem.load_plugins", f"Loaded plugin: {module_name}")
                else:
                    _dlog("PluginSystem.load_plugins",
                          f"Plugin {module_name} has no register() — skipped")
            except Exception as exc:
                _dlog("PluginSystem.load_plugins",
                      f"Failed to load plugin {module_name}: {exc}")

    def loaded_plugin_names(self) -> list[str]:
        return list(self._loaded)

    def plugin_info(self, name: str) -> dict:
        """Return {'version': str, 'description': str} for a loaded plugin."""
        return self._info.get(name, {"version": "", "description": ""})
