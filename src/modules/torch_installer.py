"""First-run torch installer for the frozen app.

torch/torchvision are excluded from the PyInstaller bundle (see SConstruct,
TORCH_EXCLUDE_MODULES) to keep the installer ~3.5 GB smaller. This module
installs them into _internal/ on first start, using the bundled portable
Python runtime (tools/python/) the same way install_plugin_deps.bat does for
plugin dependencies. See docs/TorchBundle_Analysis.md for the full analysis.
"""

import os
import subprocess
import sys

from PyQt6.QtCore import QThread, pyqtSignal #type: ignore

from app_debug import dlog as _dlog

_TAG = "torch_installer"

TORCH_INDEX_URLS = {
    "cpu":   "https://download.pytorch.org/whl/cpu",
    "cu128": "https://download.pytorch.org/whl/cu128",
}


def is_frozen() -> bool:
    """Return True when running as a PyInstaller-frozen build."""
    return bool(getattr(sys, "frozen", False))


def app_root() -> str:
    """Return the frozen app's install directory (parent of _internal/, tools/)."""
    return os.path.dirname(sys.executable)


def internal_dir() -> str:
    return os.path.join(app_root(), "_internal")


def portable_python_exe() -> str:
    """Path to the bundled portable Python used to install plugin/torch deps."""
    return os.path.join(app_root(), "tools", "python", "python.exe")


def is_torch_installed() -> bool:
    """Return True when a torch/ package folder is already present in _internal/."""
    return os.path.isdir(os.path.join(internal_dir(), "torch"))


# Stdlib dirs in tools/python/Lib we never need to mirror into _internal/.
_STDLIB_SKIP = {"test", "idlelib", "tkinter", "__pycache__", "site-packages", "lib2to3"}


def ensure_stdlib_complete() -> None:
    """Copy any stdlib modules torch needs that PyInstaller's base_library.zip lacks.

    torch is excluded from PyInstaller's Analysis (see SConstruct), so its
    deep, conditionally-imported stdlib dependencies (unittest.mock, timeit,
    etc.) are never auto-discovered and end up missing from _internal/ at
    runtime (ModuleNotFoundError/ImportError only surfaces once torch tries to
    import them). The bundled portable Python (tools/python/Lib/) already has
    a complete, working stdlib, so mirror any top-level entries not already
    present in _internal/ rather than hidden-import-ing modules one at a time.
    """
    if not is_frozen():
        return
    lib_dir = os.path.join(app_root(), "tools", "python", "Lib")
    if not os.path.isdir(lib_dir):
        return
    dest_dir = internal_dir()
    for name in os.listdir(lib_dir):
        if name in _STDLIB_SKIP or name.endswith(".dist-info"):
            continue
        dest = os.path.join(dest_dir, name)
        if os.path.exists(dest):
            continue
        src = os.path.join(lib_dir, name)
        try:
            if os.path.isdir(src):
                import shutil
                shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__"))
            else:
                import shutil
                shutil.copy2(src, dest)
            _dlog(_TAG, f"mirrored missing stdlib module into _internal/: {name}")
        except OSError as exc:
            _dlog(_TAG, f"failed to mirror stdlib module {name!r}: {exc}")


def detect_torch_index_url() -> str:
    """Return the pip --index-url for this machine's GPU, mirroring cli.bat's logic."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "-L"], capture_output=True, text=True, timeout=10, check=False,
        )
        if out.returncode == 0 and "NVIDIA" in out.stdout.upper():
            return TORCH_INDEX_URLS["cu128"]
        return TORCH_INDEX_URLS["cpu"]
    except (OSError, subprocess.TimeoutExpired) as exc:
        _dlog(_TAG, f"nvidia-smi unavailable ({exc}), falling back to CIM detection")

    try:
        out = subprocess.run(
            [
                "powershell", "-NoProfile", "-Command",
                "Get-CimInstance Win32_VideoController | "
                "Where-Object { $_.Name -notlike '*Remote*' -and $_.Name -notlike '*Virtual*' } | "
                "Select-Object -First 1 -ExpandProperty Name",
            ],
            capture_output=True, text=True, timeout=15, check=False,
        )
        if "NVIDIA" in out.stdout.upper():
            return TORCH_INDEX_URLS["cu128"]
    except (OSError, subprocess.TimeoutExpired) as exc:
        _dlog(_TAG, f"CIM GPU detection failed ({exc}), defaulting to CPU wheel")

    return TORCH_INDEX_URLS["cpu"]


class TorchInstallWorker(QThread):
    """Installs torch+torchvision into _internal/ using the bundled portable Python."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def run(self) -> None:
        python_exe = portable_python_exe()
        if not os.path.isfile(python_exe):
            self.finished.emit(False, f"Bundled Python runtime not found: {python_exe}")
            return

        index_url = detect_torch_index_url()
        self.progress.emit(f"Installing torch from {index_url} ...")
        _dlog(_TAG, f"installing torch via {python_exe} --index-url {index_url}")

        cmd = [
            python_exe, "-m", "pip", "install",
            "--target", internal_dir(),
            "torch", "torchvision",
            "--index-url", index_url,
        ]
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, creationflags=subprocess.CREATE_NO_WINDOW,
            )
            for line in proc.stdout or []:
                self.progress.emit(line.rstrip())
            proc.wait()
        except OSError as exc:
            self.finished.emit(False, f"Failed to launch torch install: {exc}")
            return

        if proc.returncode == 0 and is_torch_installed():
            self.finished.emit(True, "torch installed successfully.")
        else:
            self.finished.emit(False, f"torch install failed (exit code {proc.returncode}).")
