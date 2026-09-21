"""Input validation helpers used by the GUI panels and dialogs."""
from __future__ import annotations

import re
from typing import Optional

from models.automaton import EPSILON, Automaton

_NAME_RE = re.compile(r"^[A-Za-z0-9_\-]+$")


def validate_state_name(name: str, automaton: Automaton, editing: Optional[str] = None) -> Optional[str]:
    name = name.strip()
    if not name:
        return "El nombre del estado no puede estar vacío."
    if not _NAME_RE.match(name):
        return "El nombre sólo puede contener letras, números, '_' y '-'."
    if name != editing and name in automaton.states:
        return f"El estado '{name}' ya existe."
    return None


def validate_symbol(symbol: str, automaton: Automaton) -> Optional[str]:
    symbol = symbol.strip()
    if not symbol:
        return "El símbolo no puede estar vacío."
    if symbol == EPSILON:
        return "Ese símbolo está reservado para transiciones épsilon."
    if len(symbol) != 1:
        return "Se recomienda usar símbolos de un solo carácter."
    if symbol in automaton.alphabet:
        return f"El símbolo '{symbol}' ya está en el alfabeto."
    return None


def validate_transition(source: str, symbol: str, target: str, automaton: Automaton, allow_epsilon: bool = True) -> Optional[str]:
    if source not in automaton.states:
        return f"El estado origen '{source}' no existe."
    if target not in automaton.states:
        return f"El estado destino '{target}' no existe."
    if symbol == EPSILON:
        if not allow_epsilon:
            return "Las transiciones épsilon no están permitidas en un AFD."
        return None
    if symbol not in automaton.alphabet:
        return f"El símbolo '{symbol}' no pertenece al alfabeto."
    return None


def validate_input_string(text: str, automaton: Automaton) -> Optional[str]:
    for ch in text:
        if ch not in automaton.alphabet:
            return f"El carácter '{ch}' no pertenece al alfabeto del autómata."
    return None
