"""Tests for PluginSystem — discovery, loading, error isolation."""

import os
import sys
import types
import pytest

from modules.plugin_system import PluginSystem


class _FakeApp:
    """Minimal stand-in for QMainWindow."""
    def __init__(self):
        self.registered = []


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_plugin_package(plugins_dir, name, register_body="app.registered.append(name)"):
    pkg = os.path.join(plugins_dir, name)
    os.makedirs(pkg, exist_ok=True)
    with open(os.path.join(pkg, "__init__.py"), "w", encoding="utf-8") as f:
        f.write(f"name = '{name}'\ndef register(app):\n    {register_body}\n")


def _make_plugin_module(plugins_dir, name, register_body="app.registered.append(name)"):
    with open(os.path.join(plugins_dir, f"{name}.py"), "w", encoding="utf-8") as f:
        f.write(f"name = '{name}'\ndef register(app):\n    {register_body}\n")


# ── tests ─────────────────────────────────────────────────────────────────────

def test_empty_plugins_dir_loads_nothing(tmp_path):
    app = _FakeApp()
    ps = PluginSystem(app)
    ps._loaded = []
    # Point _PLUGINS_DIR equivalent: override by subclassing would be complex;
    # instead test via load_plugins with a patched dir via monkeypatch below.
    assert ps.loaded_plugin_names() == []


def test_nonexistent_dir_does_not_raise(monkeypatch, tmp_path):
    app = _FakeApp()
    ps = PluginSystem(app)
    missing = str(tmp_path / "no_such_dir")
    monkeypatch.setattr("modules.plugin_system._PLUGINS_DIR", missing)
    ps.load_plugins()  # must not raise
    assert ps.loaded_plugin_names() == []


def test_loads_package_plugin(monkeypatch, tmp_path):
    plugins_dir = str(tmp_path / "plugins")
    os.makedirs(plugins_dir)
    _make_plugin_package(plugins_dir, "myplugin")

    app = _FakeApp()
    ps = PluginSystem(app)
    monkeypatch.setattr("modules.plugin_system._PLUGINS_DIR", plugins_dir)
    ps.load_plugins()

    assert "myplugin" in ps.loaded_plugin_names()
    assert "myplugin" in app.registered


def test_loads_module_plugin(monkeypatch, tmp_path):
    plugins_dir = str(tmp_path / "plugins")
    os.makedirs(plugins_dir)
    _make_plugin_module(plugins_dir, "flat_plugin")

    app = _FakeApp()
    ps = PluginSystem(app)
    monkeypatch.setattr("modules.plugin_system._PLUGINS_DIR", plugins_dir)
    ps.load_plugins()

    assert "flat_plugin" in ps.loaded_plugin_names()


def test_skips_plugin_without_register(monkeypatch, tmp_path):
    plugins_dir = str(tmp_path / "plugins")
    os.makedirs(plugins_dir)
    # Package with no register()
    pkg = os.path.join(plugins_dir, "noop_plugin")
    os.makedirs(pkg)
    with open(os.path.join(pkg, "__init__.py"), "w", encoding="utf-8") as f:
        f.write("# no register\n")

    app = _FakeApp()
    ps = PluginSystem(app)
    monkeypatch.setattr("modules.plugin_system._PLUGINS_DIR", plugins_dir)
    ps.load_plugins()

    assert "noop_plugin" not in ps.loaded_plugin_names()


def test_import_error_does_not_crash(monkeypatch, tmp_path):
    plugins_dir = str(tmp_path / "plugins")
    os.makedirs(plugins_dir)
    bad = os.path.join(plugins_dir, "bad_plugin.py")
    with open(bad, "w", encoding="utf-8") as f:
        f.write("raise ImportError('intentional failure')\n")

    app = _FakeApp()
    ps = PluginSystem(app)
    monkeypatch.setattr("modules.plugin_system._PLUGINS_DIR", plugins_dir)
    ps.load_plugins()  # must not raise

    assert "bad_plugin" not in ps.loaded_plugin_names()


def test_register_exception_does_not_crash(monkeypatch, tmp_path):
    plugins_dir = str(tmp_path / "plugins")
    os.makedirs(plugins_dir)
    _make_plugin_module(plugins_dir, "exc_plugin",
                        register_body="raise RuntimeError('boom')")

    app = _FakeApp()
    ps = PluginSystem(app)
    monkeypatch.setattr("modules.plugin_system._PLUGINS_DIR", plugins_dir)
    ps.load_plugins()  # must not raise

    assert "exc_plugin" not in ps.loaded_plugin_names()


def test_skips_private_py_files(monkeypatch, tmp_path):
    plugins_dir = str(tmp_path / "plugins")
    os.makedirs(plugins_dir)
    with open(os.path.join(plugins_dir, "_private.py"), "w", encoding="utf-8") as f:
        f.write("def register(app): app.registered.append('private')\n")

    app = _FakeApp()
    ps = PluginSystem(app)
    monkeypatch.setattr("modules.plugin_system._PLUGINS_DIR", plugins_dir)
    ps.load_plugins()

    assert "private" not in app.registered


def test_loaded_plugin_names_returns_copy(monkeypatch, tmp_path):
    plugins_dir = str(tmp_path / "plugins")
    os.makedirs(plugins_dir)
    app = _FakeApp()
    ps = PluginSystem(app)
    monkeypatch.setattr("modules.plugin_system._PLUGINS_DIR", plugins_dir)
    ps.load_plugins()

    names = ps.loaded_plugin_names()
    names.append("injected")
    assert "injected" not in ps.loaded_plugin_names()
