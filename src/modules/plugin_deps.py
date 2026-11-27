"""Auto-installs missing third-party packages declared in plugins' requirements.txt.

Reuses the same bundled-pip mechanism as modules/torch_installer.py (portable
Python in tools/python/ when frozen, the active venv's Python when running
from source). See docs/PluginAutoInstallDeps_Analysis.md for the full analysis.
"""

import os
import subprocess
import sys
from importlib import metadata

from PyQt6.QtCore import QThread, pyqtSignal #type: ignore

from app_debug import dlog as _dlog
from modules import torch_installer
from modules.plugin_system import plugins_dir

_TAG = "plugin_deps"


def _iter_requirement_files():
    """Yield (plugin_name, requirements.txt path) for every discovered plugin that has one."""
    root = plugins_dir()
    if not os.path.isdir(root):
        return
    for entry in sorted(os.listdir(root)):
        req_path = os.path.join(root, entry, "requirements.txt")
        if os.path.isfile(req_path):
            yield entry, req_path


def _parse_requirement_lines(req_path: str) -> list[str]:
    """Return the requirement strings in *req_path* (comments/blank lines stripped)."""
    reqs = []
    with open(req_path, encoding="utf-8") as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if line:
                reqs.append(line)
    return reqs


def _is_satisfied(requirement: str) -> bool:
    """Return True when an already-installed distribution satisfies *requirement*."""
    try:
        from packaging.requirements import Requirement
        req = Requirement(requirement)
    except Exception as exc:
        _dlog(_TAG, f"Could not parse requirement {requirement!r}: {exc}")
        return True  # unparsable line -- don't block install on it

    try:
        installed_version = metadata.version(req.name)
    except metadata.PackageNotFoundError:
        return False

    if req.specifier and not req.specifier.contains(installed_version, prereleases=True):
        return False
    return True


def missing_requirements() -> list[str]:
    """Return the de-duplicated list of unsatisfied requirement strings across
    every discovered plugin's requirements.txt."""
    missing: dict[str, str] = {}  # keyed by lowercase package name, preserves first spec seen
    for plugin_name, req_path in _iter_requirement_files():
        for requirement in _parse_requirement_lines(req_path):
            if _is_satisfied(requirement):
                continue
            try:
                from packaging.requirements import Requirement
                key = Requirement(requirement).name.lower()
            except Exception:
                key = requirement.lower()
            if key not in missing:
                missing[key] = requirement
                _dlog(_TAG, f"{plugin_name}: missing requirement {requirement!r}")
    return list(missing.values())


def install_target_dir() -> str | None:
    """pip --target dir when frozen, or None to install into the active venv."""
    if torch_installer.is_frozen():
        return torch_installer.internal_dir()
    return None


def install_python_exe() -> str:
    """Python used to run pip -- bundled portable runtime when frozen, else this venv."""
    if torch_installer.is_frozen():
        return torch_installer.portable_python_exe()
    return sys.executable


class PluginDepsInstallWorker(QThread):
    """Installs every plugin's missing requirements.txt packages in one pip call."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, requirements: list[str], parent=None) -> None:
        super().__init__(parent)
        self._requirements = requirements

    def run(self) -> None:
        python_exe = install_python_exe()
        if not os.path.isfile(python_exe):
            self.finished.emit(False, f"Python runtime not found: {python_exe}")
            return

        cmd = [python_exe, "-m", "pip", "install"]
        target = install_target_dir()
        if target:
            cmd += ["--target", target]
        cmd += self._requirements

        self.progress.emit("Installing plugin dependencies: " + ", ".join(self._requirements))
        _dlog(_TAG, f"installing via {cmd}")

        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, creationflags=subprocess.CREATE_NO_WINDOW,
            )
            for line in proc.stdout or []:
                self.progress.emit(line.rstrip())
            proc.wait()
        except OSError as exc:
            self.finished.emit(False, f"Failed to launch plugin dependency install: {exc}")
            return

        if proc.returncode == 0:
            self.finished.emit(True, "Plugin dependencies installed successfully.")
        else:
            self.finished.emit(
                False, f"Plugin dependency install failed (exit code {proc.returncode})."
            )
