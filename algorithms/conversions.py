"""Trivial conversion helpers between the DFA and NFA views of an automaton."""
from __future__ import annotations

from models.automaton import Automaton


def dfa_to_nfa(dfa: Automaton) -> Automaton:
    """Every DFA is already a valid NFA; return an equivalent copy flagged as such."""
    nfa = dfa.clone()
    nfa.name = f"{dfa.name} (AFND equivalente)"
    return nfa


def remove_unreachable_states(automaton: Automaton) -> Automaton:
    result = automaton.clone()
    for state in result.get_unreachable_states():
        result.remove_state(state)
    return result
