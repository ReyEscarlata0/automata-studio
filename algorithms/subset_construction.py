"""NFA -> DFA conversion via the subset construction algorithm."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Tuple

from models.automaton import EPSILON, Automaton
from algorithms.simulation import epsilon_closure


def _label(states: FrozenSet[str]) -> str:
    if not states:
        return "∅"
    return "{" + ",".join(sorted(states)) + "}"


@dataclass
class SubsetStep:
    index: int
    dfa_state: str
    source_nfa_states: FrozenSet[str]
    transitions: Dict[str, str] = field(default_factory=dict)
    is_new: bool = True


@dataclass
class SubsetConstructionResult:
    dfa: Automaton
    steps: List[SubsetStep] = field(default_factory=list)
    table: List[Tuple[str, FrozenSet[str], Dict[str, str]]] = field(default_factory=list)


def nfa_to_dfa(nfa: Automaton) -> SubsetConstructionResult:
    if nfa.start_state is None:
        raise ValueError("El AFND no tiene estado inicial definido.")

    alphabet = [s for s in nfa.alphabet if s != EPSILON]
    dfa = Automaton(name=f"{nfa.name} (AFD)", alphabet=list(alphabet))

    start_closure = frozenset(epsilon_closure(nfa, {nfa.start_state}))
    dfa_state_names: Dict[FrozenSet[str], str] = {start_closure: _label(start_closure)}
    queue: List[FrozenSet[str]] = [start_closure]
    steps: List[SubsetStep] = []

    dfa.add_state(dfa_state_names[start_closure])
    dfa.set_start_state(dfa_state_names[start_closure])
    if start_closure & nfa.accept_states:
        dfa.accept_states.add(dfa_state_names[start_closure])

    processed: set = set()
    step_index = 0
    while queue:
        current = queue.pop(0)
        if current in processed:
            continue
        processed.add(current)
        current_name = dfa_state_names[current]
        step = SubsetStep(index=step_index, dfa_state=current_name, source_nfa_states=current)
        step_index += 1

        for symbol in alphabet:
            move = set()
            for state in current:
                move |= nfa.targets(state, symbol)
            target_closure = frozenset(epsilon_closure(nfa, move)) if move else frozenset()

            if not target_closure:
                step.transitions[symbol] = "∅"
                continue

            if target_closure not in dfa_state_names:
                new_name = _label(target_closure)
                dfa_state_names[target_closure] = new_name
                dfa.add_state(new_name)
                if target_closure & nfa.accept_states:
                    dfa.accept_states.add(new_name)
                queue.append(target_closure)

            target_name = dfa_state_names[target_closure]
            dfa.add_transition(current_name, symbol, target_name)
            step.transitions[symbol] = target_name

        steps.append(step)

    table = [(s.dfa_state, s.source_nfa_states, s.transitions) for s in steps]
    return SubsetConstructionResult(dfa=dfa, steps=steps, table=table)
