"""Lightweight smoke tests for the automata algorithms (run with plain python)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.automaton import Automaton, EPSILON
from algorithms.simulation import simulate
from algorithms.subset_construction import nfa_to_dfa
from algorithms.minimization import minimize_dfa
from algorithms.properties import analyze


def build_nfa_ends_with_ab() -> Automaton:
    # NFA over {a,b} accepting strings that end with "ab"
    nfa = Automaton(name="Termina en ab")
    for s in ["q0", "q1", "q2"]:
        nfa.add_state(s)
    nfa.alphabet = ["a", "b"]
    nfa.set_start_state("q0")
    nfa.accept_states = {"q2"}
    nfa.add_transition("q0", "a", "q0")
    nfa.add_transition("q0", "b", "q0")
    nfa.add_transition("q0", "a", "q1")
    nfa.add_transition("q1", "b", "q2")
    return nfa


def test_simulation():
    nfa = build_nfa_ends_with_ab()
    assert simulate(nfa, "ab").accepted
    assert simulate(nfa, "aab").accepted
    assert simulate(nfa, "aba").accepted is False
    assert simulate(nfa, "").accepted is False
    print("OK simulate NFA")


def test_subset_construction():
    nfa = build_nfa_ends_with_ab()
    result = nfa_to_dfa(nfa)
    dfa = result.dfa
    assert dfa.is_deterministic()
    for s in ["ab", "aab", "bbab", "aababab"]:
        nfa_r = simulate(nfa, s).accepted
        dfa_r = simulate(dfa, s).accepted
        assert nfa_r == dfa_r, f"mismatch on {s}: nfa={nfa_r} dfa={dfa_r}"
    for s in ["", "a", "ba", "aba", "bb"]:
        nfa_r = simulate(nfa, s).accepted
        dfa_r = simulate(dfa, s).accepted
        assert nfa_r == dfa_r, f"mismatch on {s}: nfa={nfa_r} dfa={dfa_r}"
    print("OK subset construction, steps:", len(result.steps))


def test_epsilon_nfa():
    nfa = Automaton(name="epsilon test")
    for s in ["q0", "q1", "q2"]:
        nfa.add_state(s)
    nfa.alphabet = ["a"]
    nfa.set_start_state("q0")
    nfa.accept_states = {"q2"}
    nfa.add_transition("q0", EPSILON, "q1")
    nfa.add_transition("q1", "a", "q2")
    assert simulate(nfa, "a").accepted
    assert simulate(nfa, "").accepted is False
    dfa = nfa_to_dfa(nfa).dfa
    assert dfa.is_deterministic()
    assert simulate(dfa, "a").accepted
    print("OK epsilon-NFA handling")


def test_minimization():
    # Classic textbook example: DFA over {0,1} with equivalent states to merge.
    dfa = Automaton(name="min test")
    for s in ["A", "B", "C", "D", "E", "F"]:
        dfa.add_state(s)
    dfa.alphabet = ["0", "1"]
    dfa.set_start_state("A")
    dfa.accept_states = {"C", "D", "E"}
    trans = {
        ("A", "0"): "B", ("A", "1"): "C",
        ("B", "0"): "A", ("B", "1"): "D",
        ("C", "0"): "E", ("C", "1"): "F",
        ("D", "0"): "E", ("D", "1"): "F",
        ("E", "0"): "E", ("E", "1"): "F",
        ("F", "0"): "F", ("F", "1"): "F",
    }
    for (src, sym), dst in trans.items():
        dfa.add_transition(src, sym, dst)

    result = minimize_dfa(dfa)
    min_dfa = result.dfa
    assert len(min_dfa.states) == 3, f"expected 3 states, got {len(min_dfa.states)}: {min_dfa.states}"
    for s in ["", "0", "1", "01", "10", "0011", "111", "000"]:
        orig = simulate(dfa, s).accepted
        mini = simulate(min_dfa, s).accepted
        assert orig == mini, f"mismatch on {s}: orig={orig} min={mini}"
    print("OK minimization, groups:", len(min_dfa.states))


def test_properties():
    dfa = Automaton(name="props test")
    dfa.add_state("q0")
    dfa.add_state("q1")
    dfa.add_state("unreachable")
    dfa.alphabet = ["a"]
    dfa.set_start_state("q0")
    dfa.accept_states = {"q1"}
    dfa.add_transition("q0", "a", "q1")
    dfa.add_transition("q1", "a", "q1")
    report = analyze(dfa)
    assert report.is_deterministic
    assert not report.is_connected
    assert "unreachable" in report.unreachable_states
    print("OK properties analysis")


if __name__ == "__main__":
    test_simulation()
    test_subset_construction()
    test_epsilon_nfa()
    test_minimization()
    test_properties()
    print("\nAll algorithm smoke tests passed.")
