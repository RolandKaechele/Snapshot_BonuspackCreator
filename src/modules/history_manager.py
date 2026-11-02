"""History manager — JSON-snapshot based undo/redo for the in-memory pack."""

import json

from app_debug import dlog as _dlog

_MAX_HISTORY = 50


class HistoryManager:
    """Keeps a stack of full pack-JSON snapshots to support undo/redo."""

    def __init__(self) -> None:
        self._snapshots: list[str] = []
        self._index: int = -1

    def reset(self, data: dict) -> None:
        """Start a fresh history with *data* as the single baseline state."""
        self._snapshots = [self._serialize(data)]
        self._index = 0

    def snapshot(self, data: dict) -> None:
        """Push *data* as a new state when it differs from the current one.

        Truncates any redo branch, so new edits invalidate forward history.
        """
        serialized = self._serialize(data)
        if self._index >= 0 and serialized == self._snapshots[self._index]:
            return
        self._snapshots = self._snapshots[: self._index + 1]
        self._snapshots.append(serialized)
        self._index = len(self._snapshots) - 1
        if len(self._snapshots) > _MAX_HISTORY:
            overflow = len(self._snapshots) - _MAX_HISTORY
            self._snapshots = self._snapshots[overflow:]
            self._index -= overflow
        _dlog("HistoryManager.snapshot", f"idx={self._index} depth={len(self._snapshots)}")

    def undo(self) -> dict | None:
        if self._index <= 0:
            return None
        self._index -= 1
        return self._deserialize(self._snapshots[self._index])

    def redo(self) -> dict | None:
        if self._index >= len(self._snapshots) - 1:
            return None
        self._index += 1
        return self._deserialize(self._snapshots[self._index])

    def can_undo(self) -> bool:
        return self._index > 0

    def can_redo(self) -> bool:
        return self._index < len(self._snapshots) - 1

    @staticmethod
    def _serialize(data: dict) -> str:
        return json.dumps(data, sort_keys=True, default=str)

    @staticmethod
    def _deserialize(snapshot: str) -> dict:
        return json.loads(snapshot)
