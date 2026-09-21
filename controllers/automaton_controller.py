"""Mediates between the Automaton model, algorithms, and the GUI views."""
from __future__ import annotations

from typing import List, Optional, Tuple

from PyQt6.QtCore import QObject, pyqtSignal

from algorithms import conversions, minimization, properties, subset_construction
from algorithms.simulation import SimulationResult, simulate
from models.automaton import Automaton
from utils.history import HistoryManager


class AutomatonController(QObject):
    model_changed = pyqtSignal()
    history_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.automaton = Automaton(name="Nuevo autómata")
        self.history = HistoryManager()
        self.history.on_change = self.history_changed.emit
        self._simulation_log: List[SimulationResult] = []
        self._conversion_log: List[str] = []

    # ------------------------------------------------------------------
    def _snapshot(self) -> dict:
        return self.automaton.to_dict()

    def _push_history(self) -> None:
        self.history.push(self._snapshot())

    def _notify(self) -> None:
        self.model_changed.emit()

    def replace_automaton(self, automaton: Automaton, record_history: bool = True) -> None:
        if record_history:
            self._push_history()
        self.automaton = automaton
        self._notify()

    def new_automaton(self, name: str = "Nuevo autómata") -> None:
        self._push_history()
        self.automaton = Automaton(name=name)
        self._notify()

    # ------------------------------------------------------------------
    # Mutating operations (all push history first)
    # ------------------------------------------------------------------
    def add_state(self, name: str, position: Optional[Tuple[float, float]] = None) -> None:
        self._push_history()
        try:
            self.automaton.add_state(name, position)
        except ValueError:
            self.history.undo(self._snapshot())
            raise
        self._notify()

    def remove_state(self, name: str) -> None:
        self._push_history()
        self.automaton.remove_state(name)
        self._notify()

    def rename_state(self, old: str, new: str) -> None:
        self._push_history()
        try:
            self.automaton.rename_state(old, new)
        except ValueError:
            self.history.undo(self._snapshot())
            raise
        self._notify()

    def set_start_state(self, name: str) -> None:
        self._push_history()
        self.automaton.set_start_state(name)
        self._notify()

    def toggle_accept_state(self, name: str) -> None:
        self._push_history()
        self.automaton.toggle_accept_state(name)
        self._notify()

    def add_symbol(self, symbol: str) -> None:
        self._push_history()
        try:
            self.automaton.add_symbol(symbol)
        except ValueError:
            self.history.undo(self._snapshot())
            raise
        self._notify()

    def remove_symbol(self, symbol: str) -> None:
        self._push_history()
        self.automaton.remove_symbol(symbol)
        self._notify()

    def add_transition(self, source: str, symbol: str, target: str) -> None:
        self._push_history()
        try:
            self.automaton.add_transition(source, symbol, target)
        except ValueError:
            self.history.undo(self._snapshot())
            raise
        self._notify()

    def remove_transition(self, source: str, symbol: str, target: str) -> None:
        self._push_history()
        self.automaton.remove_transition(source, symbol, target)
        self._notify()

    def move_state(self, name: str, x: float, y: float, record_history: bool = False) -> None:
        # Deliberately does not emit model_changed: this is called synchronously from
        # QGraphicsItem.itemChange while the item is mid-move, and rebuilding the scene
        # (which model_changed triggers in AutomatonGraphView) at that point crashes Qt.
        if record_history:
            self._push_history()
        self.automaton.positions[name] = (x, y)

    # ------------------------------------------------------------------
    # Undo / redo
    # ------------------------------------------------------------------
    def undo(self) -> None:
        prev = self.history.undo(self._snapshot())
        if prev is not None:
            self.automaton = Automaton.from_dict(prev)
            self._notify()

    def redo(self) -> None:
        nxt = self.history.redo(self._snapshot())
        if nxt is not None:
            self.automaton = Automaton.from_dict(nxt)
            self._notify()

    # ------------------------------------------------------------------
    # Algorithms
    # ------------------------------------------------------------------
    def simulate_string(self, text: str) -> SimulationResult:
        result = simulate(self.automaton, text)
        self._simulation_log.insert(0, result)
        self._simulation_log = self._simulation_log[:20]
        return result

    def convert_nfa_to_dfa(self) -> subset_construction.SubsetConstructionResult:
        result = subset_construction.nfa_to_dfa(self.automaton)
        self._conversion_log.insert(0, f"AFND -> AFD: '{self.automaton.name}' -> '{result.dfa.name}'")
        return result

    def convert_dfa_to_nfa(self) -> Automaton:
        result = conversions.dfa_to_nfa(self.automaton)
        self._conversion_log.insert(0, f"AFD -> AFND: '{self.automaton.name}' -> '{result.name}'")
        return result

    def minimize(self) -> minimization.MinimizationResult:
        result = minimization.minimize_dfa(self.automaton)
        self._conversion_log.insert(0, f"Minimización: '{self.automaton.name}' -> '{result.dfa.name}'")
        return result

    def analyze_properties(self) -> properties.PropertiesReport:
        return properties.analyze(self.automaton)

    @property
    def simulation_log(self) -> List[SimulationResult]:
        return self._simulation_log

    @property
    def conversion_log(self) -> List[str]:
        return self._conversion_log
