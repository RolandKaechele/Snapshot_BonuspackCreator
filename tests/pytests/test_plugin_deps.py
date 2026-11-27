"""Tests for modules.plugin_deps — requirement parsing, satisfaction check, install paths."""

import os
import sys

import pytest

from modules import plugin_deps, torch_installer


def _write_requirements(plugin_dir, lines):
    os.makedirs(plugin_dir, exist_ok=True)
    with open(os.path.join(plugin_dir, "requirements.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ── _iter_requirement_files / missing_requirements ────────────────────────────

def test_missing_requirements_empty_when_no_plugins_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(plugin_deps, "plugins_dir", lambda: str(tmp_path / "no_such_dir"))
    assert plugin_deps.missing_requirements() == []


def test_missing_requirements_skips_plugins_without_requirements_file(monkeypatch, tmp_path):
    os.makedirs(tmp_path / "plugin_a")
    monkeypatch.setattr(plugin_deps, "plugins_dir", lambda: str(tmp_path))
    assert plugin_deps.missing_requirements() == []


def test_missing_requirements_detects_uninstalled_package(monkeypatch, tmp_path):
    _write_requirements(tmp_path / "plugin_a", ["totally_not_a_real_package_xyz>=1.0"])
    monkeypatch.setattr(plugin_deps, "plugins_dir", lambda: str(tmp_path))
    assert plugin_deps.missing_requirements() == ["totally_not_a_real_package_xyz>=1.0"]


def test_missing_requirements_satisfied_package_is_skipped(monkeypatch, tmp_path):
    # pytest is always installed in this test environment.
    _write_requirements(tmp_path / "plugin_a", ["pytest>=1.0"])
    monkeypatch.setattr(plugin_deps, "plugins_dir", lambda: str(tmp_path))
    assert plugin_deps.missing_requirements() == []


def test_missing_requirements_unsatisfied_version_is_reported(monkeypatch, tmp_path):
    _write_requirements(tmp_path / "plugin_a", ["pytest>=999.0"])
    monkeypatch.setattr(plugin_deps, "plugins_dir", lambda: str(tmp_path))
    assert plugin_deps.missing_requirements() == ["pytest>=999.0"]


def test_missing_requirements_deduplicates_across_plugins(monkeypatch, tmp_path):
    _write_requirements(tmp_path / "plugin_a", ["totally_not_a_real_package_xyz>=1.0"])
    _write_requirements(tmp_path / "plugin_b", ["totally_not_a_real_package_xyz>=1.0"])
    monkeypatch.setattr(plugin_deps, "plugins_dir", lambda: str(tmp_path))
    assert plugin_deps.missing_requirements() == ["totally_not_a_real_package_xyz>=1.0"]


def test_missing_requirements_ignores_comments_and_blank_lines(monkeypatch, tmp_path):
    _write_requirements(
        tmp_path / "plugin_a",
        ["# a comment", "", "pytest>=1.0", "  # another comment"],
    )
    monkeypatch.setattr(plugin_deps, "plugins_dir", lambda: str(tmp_path))
    assert plugin_deps.missing_requirements() == []


# ── install_target_dir / install_python_exe ───────────────────────────────────

def test_install_target_dir_none_when_not_frozen(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert plugin_deps.install_target_dir() is None


def test_install_target_dir_internal_when_frozen(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "app.exe"))
    assert plugin_deps.install_target_dir() == torch_installer.internal_dir()


def test_install_python_exe_is_sys_executable_when_not_frozen(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert plugin_deps.install_python_exe() == sys.executable


def test_install_python_exe_is_portable_python_when_frozen(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "app.exe"))
    assert plugin_deps.install_python_exe() == torch_installer.portable_python_exe()
