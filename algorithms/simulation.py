"""Step-by-step simulation of DFAs and NFAs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet, List, Optional, Set

from models.automaton import EPSILON, Automaton


@dataclass
class SimulationStep:
    index: int
    symbol: Optional[str]
    from_states: Set[str]
    to_states: Set[str]
    description: str


@dataclass
class SimulationResult:
    input_string: str
    accepted: bool
    steps: List[SimulationStep] = field(default_factory=list)
    final_states: Set[str] = field(default_factory=set)
    error: Optional[str] = None


def epsilon_closure(automaton: Automaton, states: Set[str]) -> Set[str]:
    closure = set(states)
    stack = list(states)
    while stack:
        state = stack.pop()
        for target in automaton.targets(state, EPSILON):
            if target not in closure:
                closure.add(target)
                stack.append(target)
    return closure


def simulate(automaton: Automaton, input_string: str) -> SimulationResult:
    """Simulate any automaton (DFA or NFA) by tracking a set of active states."""
    if automaton.start_state is None:
        return SimulationResult(input_string, False, error="El autómata no tiene estado inicial.")

    steps: List[SimulationStep] = []
    current = epsilon_closure(automaton, {automaton.start_state})
    steps.append(SimulationStep(
        index=0, symbol=None, from_states=set(), to_states=set(current),
        description=f"Estado inicial (cierre-ε): {{{', '.join(sorted(current))}}}",
    ))

    for i, symbol in enumerate(input_string, start=1):
        if symbol not in automaton.alphabet:
            return SimulationResult(
                input_string, False, steps,
                error=f"El símbolo '{symbol}' no pertenece al alfabeto.",
            )
        next_states: Set[str] = set()
        for state in current:
            next_states |= automaton.targets(state, symbol)
        next_states = epsilon_closure(automaton, next_states)
        steps.append(SimulationStep(
            index=i, symbol=symbol, from_states=set(current), to_states=set(next_states),
            description=(
                f"Con '{symbol}': {{{', '.join(sorted(current)) or '∅'}}} -> "
                f"{{{', '.join(sorted(next_states)) or '∅'}}}"
            ),
        ))
        current = next_states
        if not current:
            break

    accepted = bool(current & automaton.accept_states)
    return SimulationResult(input_string, accepted, steps, final_states=current)
