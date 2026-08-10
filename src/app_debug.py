"""Central debug flag and logging helper."""

_debug_enabled = False


def set_debug(enabled: bool) -> None:
    global _debug_enabled
    _debug_enabled = enabled


def is_debug() -> bool:
    return _debug_enabled


def dlog(tag: str, message: str) -> None:
    if _debug_enabled:
        print(f"[{tag}] {message}")
