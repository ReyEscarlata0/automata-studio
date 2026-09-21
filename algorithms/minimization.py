"""DFA minimization via partition refinement (Moore's algorithm)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Set

from models.automaton import Automaton


@dataclass
class PartitionStep:
    index: int
    groups: List[FrozenSet[str]]
    description: str


@dataclass
class MinimizationResult:
    dfa: Automaton
    steps: List[PartitionStep] = field(default_factory=list)
    removed_unreachable: Set[str] = field(default_factory=set)
    group_of_state: Dict[str, int] = field(default_factory=dict)


def minimize_dfa(dfa: Automaton) -> MinimizationResult:
    if not dfa.is_deterministic():
        raise ValueError("Sólo se pueden minimizar autómatas deterministas (AFD).")
    if dfa.start_state is None:
        raise ValueError("El AFD no tiene estado inicial definido.")

    reachable = dfa.get_reachable_states()
    unreachable = set(dfa.states) - reachable
    working = dfa.clone()
    for s in unreachable:
        working.remove_state(s)

    alphabet = list(working.alphabet)
    steps: List[PartitionStep] = []

    accepting = frozenset(s for s in working.states if s in working.accept_states)
    non_accepting = frozenset(s for s in working.states if s not in working.accept_states)
    partition: List[FrozenSet[str]] = [g for g in (accepting, non_accepting) if g]
    steps.append(PartitionStep(
        index=0, groups=list(partition),
        description="Partición inicial: estados de aceptación vs. no aceptación.",
    ))

    def group_index(state: str, part: List[FrozenSet[str]]) -> int:
        for i, group in enumerate(part):
            if state in group:
                return i
        return -1

    changed = True
    iteration = 1
    while changed:
        changed = False
        new_partition: List[FrozenSet[str]] = []
        for group in partition:
            subgroups: Dict[tuple, Set[str]] = {}
            for state in group:
                signature = tuple(
                    group_index(next(iter(working.targets(state, sym)), None), partition)
                    if working.targets(state, sym) else -1
                    for sym in alphabet
                )
                subgroups.setdefault(signature, set()).add(state)
            if len(subgroups) > 1:
                changed = True
            for sub in subgroups.values():
                new_partition.append(frozenset(sub))
        if changed:
            partition = new_partition
            steps.append(PartitionStep(
                index=iteration, groups=list(partition),
                description=f"Refinamiento #{iteration}: se distinguen {len(partition)} grupos.",
            ))
            iteration += 1

    group_names: Dict[FrozenSet[str], str] = {}
    for i, group in enumerate(partition):
        group_names[group] = "{" + ",".join(sorted(group)) + "}"

    min_dfa = Automaton(name=f"{dfa.name} (mínimo)", alphabet=list(alphabet))
    for group in partition:
        min_dfa.add_state(group_names[group])
    for group in partition:
        representative = next(iter(group))
        name = group_names[group]
        if representative in (working.accept_states):
            min_dfa.accept_states.add(name)
        if working.start_state in group:
            min_dfa.start_state = name
        for sym in alphabet:
            targets = working.targets(representative, sym)
            if targets:
                target_state = next(iter(targets))
                target_group = partition[group_index(target_state, partition)]
                min_dfa.add_transition(name, sym, group_names[target_group])

    group_of_state = {}
    for i, group in enumerate(partition):
        for state in group:
            group_of_state[state] = i

    return MinimizationResult(
        dfa=min_dfa, steps=steps, removed_unreachable=unreachable, group_of_state=group_of_state,
    )
