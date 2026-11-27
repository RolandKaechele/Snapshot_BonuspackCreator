"""Central debug flag and logging helper."""

import datetime
import os
import sys

_debug_enabled = False
_log_file = None  # open file handle, set via enable_file_logging()


def set_debug(enabled: bool) -> None:
    global _debug_enabled
    _debug_enabled = enabled


def is_debug() -> bool:
    return _debug_enabled


def default_log_path() -> str:
    """Return where the debug log file goes -- next to the exe when frozen, else project root.

    Frozen --windowed builds have no console, so dlog()'s print() goes nowhere;
    this gives --debug users a file to inspect instead.
    """
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "debug.log")


def enable_file_logging(path: str | None = None) -> str:
    """Open (truncating) a debug log file; dlog() writes every entry to it too.

    Returns the resolved log path. Safe to call when the file can't be created
    (e.g. read-only install dir) -- dlog() just falls back to print()-only.
    """
    global _log_file
    path = path or default_log_path()
    try:
        _log_file = open(path, "w", encoding="utf-8")
        _log_file.write(
            f"=== Snapshot Pack Creator debug log started {datetime.datetime.now().isoformat()} ===\n"
        )
        _log_file.flush()
    except OSError:
        _log_file = None
    return path


def dlog(tag: str, message: str) -> None:
    if not _debug_enabled:
        return
    line = f"[{tag}] {message}"
    try:
        print(line)
    except OSError:
        pass
    if _log_file is not None:
        try:
            _log_file.write(line + "\n")
            _log_file.flush()
        except OSError:
            pass
