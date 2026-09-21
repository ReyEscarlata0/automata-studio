"""Core data model for a finite automaton (DFA or NFA).

A single class represents both DFA and NFA: an NFA is simply an
Automaton whose transition function maps to more than one target state
for some (state, symbol) pair, and/or uses epsilon transitions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

EPSILON = "ε"


@dataclass
class Automaton:
    """Generic finite automaton (DFA or NFA).

    transitions: state -> symbol -> set of target states.
    positions: state -> (x, y) canvas coordinates, used by the graph view.
    """

    name: str = "Sin título"
    states: List[str] = field(default_factory=list)
    alphabet: List[str] = field(default_factory=list)
    start_state: Optional[str] = None
    accept_states: Set[str] = field(default_factory=set)
    transitions: Dict[str, Dict[str, Set[str]]] = field(default_factory=dict)
    positions: Dict[str, Tuple[float, float]] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------
    def add_state(self, name: str, position: Optional[Tuple[float, float]] = None) -> None:
        if name in self.states:
            raise ValueError(f"El estado '{name}' ya existe.")
        self.states.append(name)
        self.transitions[name] = {}
        if position is not None:
            self.positions[name] = position
        if self.start_state is None:
            self.start_state = name

    def remove_state(self, name: str) -> None:
        if name not in self.states:
            return
        self.states.remove(name)
        self.transitions.pop(name, None)
        self.accept_states.discard(name)
        self.positions.pop(name, None)
        if self.start_state == name:
            self.start_state = self.states[0] if self.states else None
        for src in self.transitions:
            for symbol in list(self.transitions[src].keys()):
                self.transitions[src][symbol].discard(name)
                if not self.transitions[src][symbol]:
                    del self.transitions[src][symbol]

    def rename_state(self, old: str, new: str) -> None:
        if old == new:
            return
        if new in self.states:
            raise ValueError(f"El estado '{new}' ya existe.")
        idx = self.states.index(old)
        self.states[idx] = new
        self.transitions[new] = self.transitions.pop(old)
        for src in self.transitions:
            for symbol, targets in self.transitions[src].items():
                if old in targets:
                    targets.discard(old)
                    targets.add(new)
        if self.start_state == old:
            self.start_state = new
        if old in self.accept_states:
            self.accept_states.discard(old)
            self.accept_states.add(new)
        if old in self.positions:
            self.positions[new] = self.positions.pop(old)

    def set_start_state(self, name: str) -> None:
        if name not in self.states:
            raise ValueError(f"El estado '{name}' no existe.")
        self.start_state = name

    def toggle_accept_state(self, name: str) -> None:
        if name not in self.states:
            raise ValueError(f"El estado '{name}' no existe.")
        if name in self.accept_states:
            self.accept_states.discard(name)
        else:
            self.accept_states.add(name)

    # ------------------------------------------------------------------
    # Alphabet management
    # ------------------------------------------------------------------
    def add_symbol(self, symbol: str) -> None:
        if symbol in self.alphabet:
            raise ValueError(f"El símbolo '{symbol}' ya existe.")
        self.alphabet.append(symbol)

    def remove_symbol(self, symbol: str) -> None:
        if symbol not in self.alphabet:
            return
        self.alphabet.remove(symbol)
        for src in self.transitions:
            self.transitions[src].pop(symbol, None)

    # ------------------------------------------------------------------
    # Transition management
    # ------------------------------------------------------------------
    def add_transition(self, source: str, symbol: str, target: str) -> None:
        if source not in self.states:
            raise ValueError(f"El estado origen '{source}' no existe.")
        if target not in self.states:
            raise ValueError(f"El estado destino '{target}' no existe.")
        if symbol != EPSILON and symbol not in self.alphabet:
            raise ValueError(f"El símbolo '{symbol}' no pertenece al alfabeto.")
        self.transitions.setdefault(source, {}).setdefault(symbol, set()).add(target)

    def remove_transition(self, source: str, symbol: str, target: str) -> None:
        if source in self.transitions and symbol in self.transitions[source]:
            self.transitions[source][symbol].discard(target)
            if not self.transitions[source][symbol]:
                del self.transitions[source][symbol]

    def targets(self, source: str, symbol: str) -> Set[str]:
        return set(self.transitions.get(source, {}).get(symbol, set()))

    def all_transition_rows(self) -> List[Tuple[str, str, str]]:
        rows = []
        for src in self.states:
            for symbol, dests in self.transitions.get(src, {}).items():
                for dest in dests:
                    rows.append((src, symbol, dest))
        return rows

    # ------------------------------------------------------------------
    # Analysis helpers
    # ------------------------------------------------------------------
    def has_epsilon_transitions(self) -> bool:
        return any(EPSILON in self.transitions.get(s, {}) for s in self.states)

    def is_deterministic(self) -> bool:
        if self.has_epsilon_transitions():
            return False
        for src in self.states:
            for symbol, dests in self.transitions.get(src, {}).items():
                if len(dests) > 1:
                    return False
        return True

    def is_complete(self) -> bool:
        if not self.alphabet:
            return False
        for state in self.states:
            for symbol in self.alphabet:
                if not self.targets(state, symbol):
                    return False
        return True

    def get_reachable_states(self) -> Set[str]:
        if self.start_state is None:
            return set()
        seen = {self.start_state}
        stack = [self.start_state]
        while stack:
            state = stack.pop()
            for symbol, dests in self.transitions.get(state, {}).items():
                for d in dests:
                    if d not in seen:
                        seen.add(d)
                        stack.append(d)
        return seen

    def get_unreachable_states(self) -> Set[str]:
        return set(self.states) - self.get_reachable_states()

    def get_dead_states(self) -> Set[str]:
        """States from which no accept state can ever be reached."""
        alive: Set[str] = set(self.accept_states)
        changed = True
        # Build reverse adjacency
        reverse: Dict[str, Set[str]] = {s: set() for s in self.states}
        for src in self.states:
            for symbol, dests in self.transitions.get(src, {}).items():
                for d in dests:
                    reverse.setdefault(d, set()).add(src)
        stack = list(alive)
        while stack:
            state = stack.pop()
            for pred in reverse.get(state, set()):
                if pred not in alive:
                    alive.add(pred)
                    stack.append(pred)
        return set(self.states) - alive

    def is_connected(self) -> bool:
        """All states reachable from the start state."""
        return len(self.get_unreachable_states()) == 0

    def validate(self) -> List[str]:
        errors: List[str] = []
        if not self.states:
            errors.append("El autómata no tiene estados.")
        if self.start_state is None:
            errors.append("No se ha definido un estado inicial.")
        elif self.start_state not in self.states:
            errors.append("El estado inicial no existe en la lista de estados.")
        if not self.alphabet:
            errors.append("El alfabeto está vacío.")
        for a in self.accept_states:
            if a not in self.states:
                errors.append(f"El estado de aceptación '{a}' no existe.")
        for src, sym, dst in self.all_transition_rows():
            if sym != EPSILON and sym not in self.alphabet:
                errors.append(f"Transición ({src}, {sym}) usa un símbolo fuera del alfabeto.")
        return errors

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "states": list(self.states),
            "alphabet": list(self.alphabet),
            "start_state": self.start_state,
            "accept_states": sorted(self.accept_states),
            "transitions": {
                src: {sym: sorted(dests) for sym, dests in syms.items()}
                for src, syms in self.transitions.items()
            },
            "positions": {s: list(p) for s, p in self.positions.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Automaton":
        automaton = cls(
            name=data.get("name", "Sin título"),
            states=list(data.get("states", [])),
            alphabet=list(data.get("alphabet", [])),
            start_state=data.get("start_state"),
            accept_states=set(data.get("accept_states", [])),
        )
        automaton.transitions = {
            src: {sym: set(dests) for sym, dests in syms.items()}
            for src, syms in data.get("transitions", {}).items()
        }
        for s in automaton.states:
            automaton.transitions.setdefault(s, {})
        automaton.positions = {
            s: tuple(p) for s, p in data.get("positions", {}).items()
        }
        return automaton

    def clone(self) -> "Automaton":
        return Automaton.from_dict(self.to_dict())
