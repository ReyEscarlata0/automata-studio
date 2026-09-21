/**
 * Core data model for a finite automaton (DFA or NFA).
 *
 * Faithful JavaScript port of models/automaton.py from the desktop app.
 * A single class represents both DFA and NFA: an NFA is simply an
 * Automaton whose transition function maps to more than one target state
 * for some (state, symbol) pair, and/or uses epsilon transitions.
 */

const EPSILON = "ε";

/* ------------------------------------------------------------------ */
/* Small set helpers (Python set operators have no JS equivalent)      */
/* ------------------------------------------------------------------ */

function setUnion(a, b) {
  const out = new Set(a);
  for (const v of b) out.add(v);
  return out;
}

function setIntersection(a, b) {
  const out = new Set();
  for (const v of a) if (b.has(v)) out.add(v);
  return out;
}

function setDifference(a, b) {
  const out = new Set();
  for (const v of a) if (!b.has(v)) out.add(v);
  return out;
}

/** Deterministic ordering so labels and keys are reproducible. */
function sortedArray(iterable) {
  return Array.from(iterable).sort((x, y) => String(x).localeCompare(String(y), "en"));
}

/**
 * Separator for composite keys (state sets, transition rows). A control
 * character is used on purpose: state names are restricted to letters,
 * digits, "_" and "-", and generated names only add "{", "}" and ",", so
 * this byte can never appear inside one. That keeps "ab" and "a" + "b"
 * from ever producing the same key.
 */
const KEY_SEP = String.fromCharCode(1);

/** Canonical key for a set of states, standing in for Python frozenset. */
function setKey(iterable) {
  return sortedArray(iterable).join(KEY_SEP);
}

class Automaton {
  constructor(data) {
    const d = data || {};
    this.name = d.name !== undefined ? d.name : "Untitled";
    this.states = d.states ? d.states.slice() : [];
    this.alphabet = d.alphabet ? d.alphabet.slice() : [];
    this.startState = d.startState !== undefined ? d.startState : null;
    this.acceptStates = new Set(d.acceptStates || []);
    /** state -> symbol -> Set of target states */
    this.transitions = d.transitions || {};
    /** state -> [x, y] canvas coordinates */
    this.positions = d.positions || {};
  }

  /* ---------------------------------------------------------------- */
  /* State management                                                  */
  /* ---------------------------------------------------------------- */

  addState(name, position) {
    if (this.states.indexOf(name) !== -1) {
      throw new Error('State "' + name + '" already exists.');
    }
    this.states.push(name);
    this.transitions[name] = {};
    if (position) this.positions[name] = position;
    if (this.startState === null) this.startState = name;
  }

  removeState(name) {
    if (this.states.indexOf(name) === -1) return;
    this.states = this.states.filter((s) => s !== name);
    delete this.transitions[name];
    this.acceptStates.delete(name);
    delete this.positions[name];
    if (this.startState === name) {
      this.startState = this.states.length ? this.states[0] : null;
    }
    for (const src of Object.keys(this.transitions)) {
      for (const symbol of Object.keys(this.transitions[src])) {
        this.transitions[src][symbol].delete(name);
        if (this.transitions[src][symbol].size === 0) {
          delete this.transitions[src][symbol];
        }
      }
    }
  }

  renameState(oldName, newName) {
    if (oldName === newName) return;
    if (this.states.indexOf(newName) !== -1) {
      throw new Error('State "' + newName + '" already exists.');
    }
    const idx = this.states.indexOf(oldName);
    this.states[idx] = newName;
    this.transitions[newName] = this.transitions[oldName] || {};
    delete this.transitions[oldName];
    for (const src of Object.keys(this.transitions)) {
      for (const targets of Object.values(this.transitions[src])) {
        if (targets.has(oldName)) {
          targets.delete(oldName);
          targets.add(newName);
        }
      }
    }
    if (this.startState === oldName) this.startState = newName;
    if (this.acceptStates.has(oldName)) {
      this.acceptStates.delete(oldName);
      this.acceptStates.add(newName);
    }
    if (oldName in this.positions) {
      this.positions[newName] = this.positions[oldName];
      delete this.positions[oldName];
    }
  }

  setStartState(name) {
    if (this.states.indexOf(name) === -1) {
      throw new Error('State "' + name + '" does not exist.');
    }
    this.startState = name;
  }

  toggleAcceptState(name) {
    if (this.states.indexOf(name) === -1) {
      throw new Error('State "' + name + '" does not exist.');
    }
    if (this.acceptStates.has(name)) this.acceptStates.delete(name);
    else this.acceptStates.add(name);
  }

  /* ---------------------------------------------------------------- */
  /* Alphabet management                                               */
  /* ---------------------------------------------------------------- */

  addSymbol(symbol) {
    if (this.alphabet.indexOf(symbol) !== -1) {
      throw new Error('Symbol "' + symbol + '" already exists.');
    }
    this.alphabet.push(symbol);
  }

  removeSymbol(symbol) {
    if (this.alphabet.indexOf(symbol) === -1) return;
    this.alphabet = this.alphabet.filter((s) => s !== symbol);
    for (const src of Object.keys(this.transitions)) {
      delete this.transitions[src][symbol];
    }
  }

  /* ---------------------------------------------------------------- */
  /* Transition management                                             */
  /* ---------------------------------------------------------------- */

  addTransition(source, symbol, target) {
    if (this.states.indexOf(source) === -1) {
      throw new Error('Source state "' + source + '" does not exist.');
    }
    if (this.states.indexOf(target) === -1) {
      throw new Error('Target state "' + target + '" does not exist.');
    }
    if (symbol !== EPSILON && this.alphabet.indexOf(symbol) === -1) {
      throw new Error('Symbol "' + symbol + '" is not in the alphabet.');
    }
    if (!this.transitions[source]) this.transitions[source] = {};
    if (!this.transitions[source][symbol]) {
      this.transitions[source][symbol] = new Set();
    }
    this.transitions[source][symbol].add(target);
  }

  removeTransition(source, symbol, target) {
    const bySymbol = this.transitions[source];
    if (bySymbol && bySymbol[symbol]) {
      bySymbol[symbol].delete(target);
      if (bySymbol[symbol].size === 0) delete bySymbol[symbol];
    }
  }

  /** Targets reachable from source consuming exactly this symbol. */
  targets(source, symbol) {
    const bySymbol = this.transitions[source];
    if (!bySymbol || !bySymbol[symbol]) return new Set();
    return new Set(bySymbol[symbol]);
  }

  /** Flat [source, symbol, target] rows, ordered by the states list. */
  allTransitionRows() {
    const rows = [];
    for (const src of this.states) {
      const bySymbol = this.transitions[src] || {};
      for (const symbol of Object.keys(bySymbol)) {
        for (const dest of sortedArray(bySymbol[symbol])) {
          rows.push([src, symbol, dest]);
        }
      }
    }
    return rows;
  }

  /* ---------------------------------------------------------------- */
  /* Analysis helpers                                                  */
  /* ---------------------------------------------------------------- */

  hasEpsilonTransitions() {
    return this.states.some((s) => Boolean((this.transitions[s] || {})[EPSILON]));
  }

  isDeterministic() {
    if (this.hasEpsilonTransitions()) return false;
    for (const src of this.states) {
      const bySymbol = this.transitions[src] || {};
      for (const dests of Object.values(bySymbol)) {
        if (dests.size > 1) return false;
      }
    }
    return true;
  }

  isComplete() {
    if (!this.alphabet.length) return false;
    for (const state of this.states) {
      for (const symbol of this.alphabet) {
        if (this.targets(state, symbol).size === 0) return false;
      }
    }
    return true;
  }

  getReachableStates() {
    if (this.startState === null) return new Set();
    const seen = new Set([this.startState]);
    const stack = [this.startState];
    while (stack.length) {
      const state = stack.pop();
      const bySymbol = this.transitions[state] || {};
      for (const dests of Object.values(bySymbol)) {
        for (const d of dests) {
          if (!seen.has(d)) {
            seen.add(d);
            stack.push(d);
          }
        }
      }
    }
    return seen;
  }

  getUnreachableStates() {
    return setDifference(new Set(this.states), this.getReachableStates());
  }

  /** States from which no accept state can ever be reached. */
  getDeadStates() {
    const alive = new Set(this.acceptStates);
    const reverse = {};
    for (const s of this.states) reverse[s] = new Set();
    for (const src of this.states) {
      const bySymbol = this.transitions[src] || {};
      for (const dests of Object.values(bySymbol)) {
        for (const d of dests) {
          if (!reverse[d]) reverse[d] = new Set();
          reverse[d].add(src);
        }
      }
    }
    const stack = Array.from(alive);
    while (stack.length) {
      const state = stack.pop();
      for (const pred of reverse[state] || []) {
        if (!alive.has(pred)) {
          alive.add(pred);
          stack.push(pred);
        }
      }
    }
    return setDifference(new Set(this.states), alive);
  }

  /** True when every state is reachable from the start state. */
  isConnected() {
    return this.getUnreachableStates().size === 0;
  }

  validate() {
    const errors = [];
    if (!this.states.length) errors.push("The automaton has no states.");
    if (this.startState === null) {
      errors.push("No start state has been defined.");
    } else if (this.states.indexOf(this.startState) === -1) {
      errors.push("The start state is not in the list of states.");
    }
    if (!this.alphabet.length) errors.push("The alphabet is empty.");
    for (const a of sortedArray(this.acceptStates)) {
      if (this.states.indexOf(a) === -1) {
        errors.push('Accept state "' + a + '" does not exist.');
      }
    }
    for (const row of this.allTransitionRows()) {
      const src = row[0];
      const sym = row[1];
      if (sym !== EPSILON && this.alphabet.indexOf(sym) === -1) {
        errors.push("Transition (" + src + ", " + sym + ") uses a symbol outside the alphabet.");
      }
    }
    return errors;
  }

  /* ---------------------------------------------------------------- */
  /* Serialization - the .afjson format shared with the desktop app    */
  /* ---------------------------------------------------------------- */

  toJSON() {
    const transitions = {};
    for (const src of Object.keys(this.transitions)) {
      transitions[src] = {};
      for (const sym of Object.keys(this.transitions[src])) {
        transitions[src][sym] = sortedArray(this.transitions[src][sym]);
      }
    }
    const positions = {};
    for (const entry of Object.entries(this.positions)) {
      positions[entry[0]] = [entry[1][0], entry[1][1]];
    }
    return {
      name: this.name,
      states: this.states.slice(),
      alphabet: this.alphabet.slice(),
      start_state: this.startState,
      accept_states: sortedArray(this.acceptStates),
      transitions: transitions,
      positions: positions,
    };
  }

  static fromJSON(data) {
    const automaton = new Automaton({
      name: data.name !== undefined ? data.name : "Untitled",
      states: data.states || [],
      alphabet: data.alphabet || [],
      startState: data.start_state !== undefined ? data.start_state : null,
      acceptStates: data.accept_states || [],
    });
    const transitions = {};
    for (const entry of Object.entries(data.transitions || {})) {
      const src = entry[0];
      transitions[src] = {};
      for (const sub of Object.entries(entry[1])) {
        transitions[src][sub[0]] = new Set(sub[1]);
      }
    }
    automaton.transitions = transitions;
    for (const s of automaton.states) {
      if (!automaton.transitions[s]) automaton.transitions[s] = {};
    }
    const positions = {};
    for (const entry of Object.entries(data.positions || {})) {
      positions[entry[0]] = [entry[1][0], entry[1][1]];
    }
    automaton.positions = positions;
    return automaton;
  }

  clone() {
    return Automaton.fromJSON(this.toJSON());
  }
}
