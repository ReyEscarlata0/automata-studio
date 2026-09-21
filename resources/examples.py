"""Preloaded example automatons for learning and quick testing."""
from __future__ import annotations

from typing import Dict

from models.automaton import EPSILON

EXAMPLES: Dict[str, dict] = {
    "AFD: termina en 1": {
        "name": "AFD: cadenas binarias que terminan en 1",
        "states": ["q0", "q1"],
        "alphabet": ["0", "1"],
        "start_state": "q0",
        "accept_states": ["q1"],
        "transitions": {
            "q0": {"0": ["q0"], "1": ["q1"]},
            "q1": {"0": ["q0"], "1": ["q1"]},
        },
        "positions": {"q0": [100, 150], "q1": [320, 150]},
    },
    "AFD: divisible entre 3": {
        "name": "AFD: binario divisible entre 3",
        "states": ["r0", "r1", "r2"],
        "alphabet": ["0", "1"],
        "start_state": "r0",
        "accept_states": ["r0"],
        "transitions": {
            "r0": {"0": ["r0"], "1": ["r1"]},
            "r1": {"0": ["r2"], "1": ["r0"]},
            "r2": {"0": ["r1"], "1": ["r2"]},
        },
        "positions": {"r0": [220, 80], "r1": [80, 260], "r2": [360, 260]},
    },
    "AFND: contiene 'ab'": {
        "name": "AFND: contiene la subcadena 'ab'",
        "states": ["s0", "s1", "s2"],
        "alphabet": ["a", "b"],
        "start_state": "s0",
        "accept_states": ["s2"],
        "transitions": {
            "s0": {"a": ["s0", "s1"], "b": ["s0"]},
            "s1": {"b": ["s2"]},
            "s2": {"a": ["s2"], "b": ["s2"]},
        },
        "positions": {"s0": [80, 150], "s1": [280, 60], "s2": [480, 150]},
    },
    "AFND-ε: a*b* ∪ b*a*": {
        "name": "AFND con epsilon: a*b* union b*a*",
        "states": ["p0", "p1", "p2", "p3", "p4"],
        "alphabet": ["a", "b"],
        "start_state": "p0",
        "accept_states": ["p2", "p4"],
        "transitions": {
            "p0": {EPSILON: ["p1", "p3"]},
            "p1": {"a": ["p1"], "b": ["p2"]},
            "p2": {"b": ["p2"]},
            "p3": {"b": ["p3"], "a": ["p4"]},
            "p4": {"a": ["p4"]},
        },
        "positions": {
            "p0": [60, 200], "p1": [220, 80], "p2": [400, 80],
            "p3": [220, 320], "p4": [400, 320],
        },
    },
    "AFD: con estados muertos e inaccesibles": {
        "name": "AFD de ejemplo con estados muertos e inaccesibles",
        "states": ["A", "B", "C", "D", "E"],
        "alphabet": ["0", "1"],
        "start_state": "A",
        "accept_states": ["B"],
        "transitions": {
            "A": {"0": ["A"], "1": ["B"]},
            "B": {"0": ["B"], "1": ["B"]},
            "C": {"0": ["D"], "1": ["D"]},
            "D": {"0": ["D"], "1": ["D"]},
            "E": {"0": ["A"], "1": ["A"]},
        },
        "positions": {
            "A": [80, 200], "B": [300, 200], "C": [500, 80],
            "D": [500, 320], "E": [80, 380],
        },
    },
}
