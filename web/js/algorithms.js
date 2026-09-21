/**
 * Automaton algorithms: simulation, subset construction, minimization,
 * property analysis and trivial conversions.
 *
 * Faithful JavaScript port of the algorithms/ package of the desktop app.
 * Every function here is pure: it takes an Automaton and returns a result
 * object that also carries the intermediate steps, so the UI can show the
 * process and not only the outcome.
 */

/* ------------------------------------------------------------------ */
/* Simulation (algorithms/simulation.py)                               */
/* ------------------------------------------------------------------ */

function epsilonClosure(automaton, states) {
  const closure = new Set(states);
  const stack = Array.from(states);
  while (stack.length) {
    const state = stack.pop();
    for (const target of automaton.targets(state, EPSILON)) {
      if (!closure.has(target)) {
        closure.add(target);
        stack.push(target);
      }
    }
  }
  return closure;
}

/**
 * Simulate any automaton (DFA or NFA) by tracking a set of active states.
 * Returns { inputString, accepted, steps, finalStates, error }.
 */
function simulate(automaton, inputString) {
  if (automaton.startState === null) {
    return {
      inputString: inputString,
      accepted: false,
      steps: [],
      finalStates: new Set(),
      error: "The automaton has no start state.",
    };
  }

  const steps = [];
  let current = epsilonClosure(automaton, new Set([automaton.startState]));
  steps.push({
    index: 0,
    symbol: null,
    fromStates: new Set(),
    toStates: new Set(current),
    description: "Start state (ε-closure): {" + sortedArray(current).join(", ") + "}",
  });

  const symbols = Array.from(inputString);
  for (let i = 0; i < symbols.length; i++) {
    const symbol = symbols[i];
    if (automaton.alphabet.indexOf(symbol) === -1) {
      return {
        inputString: inputString,
        accepted: false,
        steps: steps,
        finalStates: new Set(),
        error: 'Symbol "' + symbol + '" is not in the alphabet.',
      };
    }
    let nextStates = new Set();
    for (const state of current) {
      nextStates = setUnion(nextStates, automaton.targets(state, symbol));
    }
    nextStates = epsilonClosure(automaton, nextStates);
    const fromLabel = sortedArray(current).join(", ") || "∅";
    const toLabel = sortedArray(nextStates).join(", ") || "∅";
    steps.push({
      index: i + 1,
      symbol: symbol,
      fromStates: new Set(current),
      toStates: new Set(nextStates),
      description: "On '" + symbol + "': {" + fromLabel + "} → {" + toLabel + "}",
    });
    current = nextStates;
    if (!current.size) break;
  }

  const accepted = setIntersection(current, automaton.acceptStates).size > 0;
  return {
    inputString: inputString,
    accepted: accepted,
    steps: steps,
    finalStates: current,
    error: null,
  };
}

/* ------------------------------------------------------------------ */
/* NFA -> DFA, subset construction (algorithms/subset_construction.py)  */
/* ------------------------------------------------------------------ */

function subsetLabel(states) {
  if (!states.size) return "∅";
  return "{" + sortedArray(states).join(",") + "}";
}

/**
 * Convert an NFA into an equivalent DFA by subset construction.
 * Returns { dfa, steps, table }, where each step records the DFA state
 * being expanded, the NFA states it stands for, and its transitions.
 */
function nfaToDfa(nfa) {
  if (nfa.startState === null) {
    throw new Error("The NFA has no start state defined.");
  }

  const alphabet = nfa.alphabet.filter((s) => s !== EPSILON);
  const dfa = new Automaton({ name: nfa.name + " (DFA)", alphabet: alphabet.slice() });

  const startClosure = epsilonClosure(nfa, new Set([nfa.startState]));
  const startKey = setKey(startClosure);

  /** key -> { states: Set, name: string } */
  const known = {};
  known[startKey] = { states: startClosure, name: subsetLabel(startClosure) };

  const queue = [startKey];
  const steps = [];

  dfa.addState(known[startKey].name);
  dfa.setStartState(known[startKey].name);
  if (setIntersection(startClosure, nfa.acceptStates).size) {
    dfa.acceptStates.add(known[startKey].name);
  }

  const processed = new Set();
  let stepIndex = 0;

  while (queue.length) {
    const currentKey = queue.shift();
    if (processed.has(currentKey)) continue;
    processed.add(currentKey);

    const currentStates = known[currentKey].states;
    const currentName = known[currentKey].name;
    const step = {
      index: stepIndex,
      dfaState: currentName,
      sourceNfaStates: currentStates,
      transitions: {},
    };
    stepIndex += 1;

    for (const symbol of alphabet) {
      let move = new Set();
      for (const state of currentStates) {
        move = setUnion(move, nfa.targets(state, symbol));
      }
      const targetClosure = move.size ? epsilonClosure(nfa, move) : new Set();

      if (!targetClosure.size) {
        step.transitions[symbol] = "∅";
        continue;
      }

      const targetKey = setKey(targetClosure);
      if (!(targetKey in known)) {
        const newName = subsetLabel(targetClosure);
        known[targetKey] = { states: targetClosure, name: newName };
        dfa.addState(newName);
        if (setIntersection(targetClosure, nfa.acceptStates).size) {
          dfa.acceptStates.add(newName);
        }
        queue.push(targetKey);
      }

      const targetName = known[targetKey].name;
      dfa.addTransition(currentName, symbol, targetName);
      step.transitions[symbol] = targetName;
    }

    steps.push(step);
  }

  const table = steps.map((s) => [s.dfaState, s.sourceNfaStates, s.transitions]);
  return { dfa: dfa, steps: steps, table: table };
}

/* ------------------------------------------------------------------ */
/* DFA minimization, partition refinement (algorithms/minimization.py)  */
/* ------------------------------------------------------------------ */

/**
 * Minimize a DFA with Moore partition refinement.
 * Returns { dfa, steps, removedUnreachable, groupOfState }, where steps
 * holds the partition after every refinement round.
 */
function minimizeDfa(dfa) {
  if (!dfa.isDeterministic()) {
    throw new Error("Only deterministic automata (DFA) can be minimized.");
  }
  if (dfa.startState === null) {
    throw new Error("The DFA has no start state defined.");
  }

  const reachable = dfa.getReachableStates();
  const unreachable = setDifference(new Set(dfa.states), reachable);
  const working = dfa.clone();
  for (const s of unreachable) working.removeState(s);

  const alphabet = working.alphabet.slice();
  const steps = [];

  const accepting = working.states.filter((s) => working.acceptStates.has(s));
  const nonAccepting = working.states.filter((s) => !working.acceptStates.has(s));
  let partition = [accepting, nonAccepting]
    .filter((g) => g.length)
    .map((g) => new Set(g));

  steps.push({
    index: 0,
    groups: partition.map((g) => new Set(g)),
    description: "Initial partition: accepting vs. non-accepting states.",
  });

  function groupIndex(state, part) {
    for (let i = 0; i < part.length; i++) {
      if (part[i].has(state)) return i;
    }
    return -1;
  }

  let changed = true;
  let iteration = 1;
  while (changed) {
    changed = false;
    const newPartition = [];
    for (const group of partition) {
      /** signature -> Set of states sharing it */
      const subgroups = new Map();
      for (const state of sortedArray(group)) {
        const signature = alphabet
          .map((sym) => {
            const targets = working.targets(state, sym);
            if (!targets.size) return -1;
            return groupIndex(Array.from(targets)[0], partition);
          })
          .join(",");
        if (!subgroups.has(signature)) subgroups.set(signature, new Set());
        subgroups.get(signature).add(state);
      }
      if (subgroups.size > 1) changed = true;
      for (const sub of subgroups.values()) newPartition.push(sub);
    }
    if (changed) {
      partition = newPartition;
      steps.push({
        index: iteration,
        groups: partition.map((g) => new Set(g)),
        description: "Refinement #" + iteration + ": " + partition.length + " groups distinguished.",
      });
      iteration += 1;
    }
  }

  const groupNames = partition.map((g) => "{" + sortedArray(g).join(",") + "}");

  const minDfa = new Automaton({ name: dfa.name + " (minimal)", alphabet: alphabet.slice() });
  for (const name of groupNames) minDfa.addState(name);

  for (let i = 0; i < partition.length; i++) {
    const group = partition[i];
    const representative = sortedArray(group)[0];
    const name = groupNames[i];
    if (working.acceptStates.has(representative)) minDfa.acceptStates.add(name);
    if (group.has(working.startState)) minDfa.startState = name;
    for (const sym of alphabet) {
      const targets = working.targets(representative, sym);
      if (targets.size) {
        const targetState = Array.from(targets)[0];
        const targetGroup = groupIndex(targetState, partition);
        minDfa.addTransition(name, sym, groupNames[targetGroup]);
      }
    }
  }

  const groupOfState = {};
  for (let i = 0; i < partition.length; i++) {
    for (const state of partition[i]) groupOfState[state] = i;
  }

  return {
    dfa: minDfa,
    steps: steps,
    removedUnreachable: unreachable,
    groupOfState: groupOfState,
  };
}

/* ------------------------------------------------------------------ */
/* Property analysis (algorithms/properties.py)                        */
/* ------------------------------------------------------------------ */

function analyzeProperties(automaton) {
  const unreachable = automaton.getUnreachableStates();
  const dead = automaton.getDeadStates();
  const missing = [];
  if (automaton.alphabet.length) {
    for (const state of automaton.states) {
      for (const symbol of automaton.alphabet) {
        if (!automaton.targets(state, symbol).size) {
          missing.push(state + " --" + symbol + "--> (undefined)");
        }
      }
    }
  }
  return {
    isDeterministic: automaton.isDeterministic(),
    isComplete: automaton.isComplete(),
    isConnected: unreachable.size === 0,
    hasEpsilonTransitions: automaton.hasEpsilonTransitions(),
    unreachableStates: unreachable,
    deadStates: dead,
    missingTransitions: missing,
    validationErrors: automaton.validate(),
  };
}

/* ------------------------------------------------------------------ */
/* Trivial conversions (algorithms/conversions.py)                     */
/* ------------------------------------------------------------------ */

/** Every DFA is already a valid NFA; return an equivalent copy. */
function dfaToNfa(dfa) {
  const nfa = dfa.clone();
  nfa.name = dfa.name + " (equivalent NFA)";
  return nfa;
}

function removeUnreachableStates(automaton) {
  const result = automaton.clone();
  for (const state of result.getUnreachableStates()) {
    result.removeState(state);
  }
  return result;
}
