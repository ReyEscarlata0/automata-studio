"""Structural property analysis for an automaton."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Set

from models.automaton import Automaton


@dataclass
class PropertiesReport:
    is_deterministic: bool
    is_complete: bool
    is_connected: bool
    has_epsilon_transitions: bool
    unreachable_states: Set[str] = field(default_factory=set)
    dead_states: Set[str] = field(default_factory=set)
    missing_transitions: List[str] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)


def analyze(automaton: Automaton) -> PropertiesReport:
    unreachable = automaton.get_unreachable_states()
    dead = automaton.get_dead_states()
    missing: List[str] = []
    if automaton.alphabet:
        for state in automaton.states:
            for symbol in automaton.alphabet:
                if not automaton.targets(state, symbol):
                    missing.append(f"{state} --{symbol}--> (sin definir)")

    return PropertiesReport(
        is_deterministic=automaton.is_deterministic(),
        is_complete=automaton.is_complete(),
        is_connected=len(unreachable) == 0,
        has_epsilon_transitions=automaton.has_epsilon_transitions(),
        unreachable_states=unreachable,
        dead_states=dead,
        missing_transitions=missing,
        validation_errors=automaton.validate(),
    )
