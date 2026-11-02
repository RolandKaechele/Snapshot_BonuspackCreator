"""Plugin system — discovers and loads Python plugin packages from plugins/."""

import json
import os
import sys
import types
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


def _detected_vram_gb() -> float | None:
    """Return the primary CUDA GPU's total VRAM in GB, or None if unavailable."""
    try:
        import torch  # type: ignore
        if torch.cuda.is_available():
            return torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
    except Exception:
        pass
    return None


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
        self._modules: dict[str, types.ModuleType] = {}

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

            # Import unconditionally (even disabled/hardware-unsupported plugins) so
            # Manage Plugins can show version/description/MIN_VRAM_GB for every
            # discovered plugin — safe because plugins only do heavy imports (torch,
            # diffusers, …) lazily inside functions, never at module level.
            try:
                mod = importlib.import_module(module_name)
            except Exception as exc:
                _dlog("PluginSystem.load_plugins", f"Failed to import {module_name}: {exc}")
                continue
            self._modules[module_name] = mod
            self._info[module_name] = {
                "version": getattr(mod, "__version__", ""),
                "description": (getattr(mod, "__doc__", "") or "").strip().splitlines()[0]
                if getattr(mod, "__doc__", "") else "",
            }

            if module_name in disabled:
                _dlog("PluginSystem.load_plugins", f"Skipped disabled plugin: {module_name}")
                continue

            unsupported = self.hardware_status(module_name)
            if unsupported:
                _dlog("PluginSystem.load_plugins",
                      f"Skipped {module_name}: {unsupported}")
                continue

            try:
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

    def plugin_info(self, name: str) -> dict:
        """Return {'version': str, 'description': str} for a discovered plugin."""
        return self._info.get(name, {"version": "", "description": ""})

    def hardware_status(self, name: str) -> str:
        """Return '' when *name*'s hardware requirements are met (or it declares
        none), else a short human-readable reason it can't run on this machine.

        Convention: a plugin module may define a module-level ``MIN_VRAM_GB``
        (int/float) to opt into this check; see plugins/moss_image/__init__.py.
        """
        mod = self._modules.get(name)
        min_vram = getattr(mod, "MIN_VRAM_GB", None) if mod else None
        if not min_vram:
            return ""
        vram = _detected_vram_gb()
        if vram is None:
            return f"Requires a CUDA GPU with \u2248{min_vram:g} GB VRAM; no CUDA GPU detected"
        if vram < min_vram:
            return f"Requires \u2248{min_vram:g} GB VRAM; detected GPU has only {vram:.1f} GB"
        return ""
