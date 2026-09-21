"""Undo/redo manager based on JSON snapshots of the Automaton model."""
from __future__ import annotations

import copy
from typing import Callable, List, Optional


class HistoryManager:
    def __init__(self, max_depth: int = 100) -> None:
        self._undo_stack: List[dict] = []
        self._redo_stack: List[dict] = []
        self._max_depth = max_depth
        self.on_change: Optional[Callable[[], None]] = None

    def push(self, snapshot: dict) -> None:
        self._undo_stack.append(copy.deepcopy(snapshot))
        if len(self._undo_stack) > self._max_depth:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._notify()

    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def undo(self, current_snapshot: dict) -> Optional[dict]:
        if not self.can_undo():
            return None
        previous = self._undo_stack.pop()
        self._redo_stack.append(copy.deepcopy(current_snapshot))
        self._notify()
        return previous

    def redo(self, current_snapshot: dict) -> Optional[dict]:
        if not self.can_redo():
            return None
        nxt = self._redo_stack.pop()
        self._undo_stack.append(copy.deepcopy(current_snapshot))
        self._notify()
        return nxt

    def clear(self) -> None:
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._notify()

    def _notify(self) -> None:
        if self.on_change:
            self.on_change()
