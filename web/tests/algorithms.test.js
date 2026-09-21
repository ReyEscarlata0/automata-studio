/**
 * Smoke tests for the ported algorithms.
 *
 * This mirrors tests/test_algorithms.py case for case: the same automata,
 * the same strings, the same expected answers. If both suites pass, the
 * JavaScript port and the Python original agree.
 *
 * Run with:  node web/tests/run-tests.js
 *
 * The file is executed inside a context where automaton.js, algorithms.js
 * and examples.js have already been evaluated, so their globals are here.
 */

let failures = 0;
let checks = 0;

function assert(condition, message) {
  checks += 1;
  if (!condition) {
    failures += 1;
    console.error("  FAIL: " + message);
  }
}

function assertEqual(actual, expected, message) {
  assert(
    actual === expected,
    message + " (expected " + JSON.stringify(expected) + ", got " + JSON.stringify(actual) + ")"
  );
}

/* ------------------------------------------------------------------ */

function buildNfaEndsWithAb() {
  // NFA over {a,b} accepting strings that end with "ab".
  const nfa = new Automaton({ name: "Ends with ab" });
  for (const s of ["q0", "q1", "q2"]) nfa.addState(s);
  nfa.alphabet = ["a", "b"];
  nfa.setStartState("q0");
  nfa.acceptStates = new Set(["q2"]);
  nfa.addTransition("q0", "a", "q0");
  nfa.addTransition("q0", "b", "q0");
  nfa.addTransition("q0", "a", "q1");
  nfa.addTransition("q1", "b", "q2");
  return nfa;
}

function testSimulation() {
  const nfa = buildNfaEndsWithAb();
  assert(simulate(nfa, "ab").accepted, 'simulate "ab" should be accepted');
  assert(simulate(nfa, "aab").accepted, 'simulate "aab" should be accepted');
  assertEqual(simulate(nfa, "aba").accepted, false, 'simulate "aba"');
  assertEqual(simulate(nfa, "").accepted, false, "simulate empty string");
  console.log("OK simulate NFA");
}

function testSubsetConstruction() {
  const nfa = buildNfaEndsWithAb();
  const result = nfaToDfa(nfa);
  const dfa = result.dfa;
  assert(dfa.isDeterministic(), "subset construction must yield a DFA");

  const strings = ["ab", "aab", "bbab", "aababab", "", "a", "ba", "aba", "bb"];
  for (const s of strings) {
    const nfaResult = simulate(nfa, s).accepted;
    const dfaResult = simulate(dfa, s).accepted;
    assertEqual(dfaResult, nfaResult, 'NFA and DFA disagree on "' + s + '"');
  }
  console.log("OK subset construction, steps: " + result.steps.length);
}

function testEpsilonNfa() {
  const nfa = new Automaton({ name: "epsilon test" });
  for (const s of ["q0", "q1", "q2"]) nfa.addState(s);
  nfa.alphabet = ["a"];
  nfa.setStartState("q0");
  nfa.acceptStates = new Set(["q2"]);
  nfa.addTransition("q0", EPSILON, "q1");
  nfa.addTransition("q1", "a", "q2");

  assert(simulate(nfa, "a").accepted, 'epsilon-NFA should accept "a"');
  assertEqual(simulate(nfa, "").accepted, false, "epsilon-NFA on empty string");

  const dfa = nfaToDfa(nfa).dfa;
  assert(dfa.isDeterministic(), "converted epsilon-NFA must be a DFA");
  assert(simulate(dfa, "a").accepted, 'converted DFA should accept "a"');
  console.log("OK epsilon-NFA handling");
}

function testMinimization() {
  // Classic textbook example: DFA over {0,1} with equivalent states to merge.
  const dfa = new Automaton({ name: "min test" });
  for (const s of ["A", "B", "C", "D", "E", "F"]) dfa.addState(s);
  dfa.alphabet = ["0", "1"];
  dfa.setStartState("A");
  dfa.acceptStates = new Set(["C", "D", "E"]);
  const trans = [
    ["A", "0", "B"], ["A", "1", "C"],
    ["B", "0", "A"], ["B", "1", "D"],
    ["C", "0", "E"], ["C", "1", "F"],
    ["D", "0", "E"], ["D", "1", "F"],
    ["E", "0", "E"], ["E", "1", "F"],
    ["F", "0", "F"], ["F", "1", "F"],
  ];
  for (const t of trans) dfa.addTransition(t[0], t[1], t[2]);

  const result = minimizeDfa(dfa);
  const minDfa = result.dfa;
  assertEqual(minDfa.states.length, 3, "minimal DFA state count");

  for (const s of ["", "0", "1", "01", "10", "0011", "111", "000"]) {
    const original = simulate(dfa, s).accepted;
    const minimal = simulate(minDfa, s).accepted;
    assertEqual(minimal, original, 'original and minimal DFA disagree on "' + s + '"');
  }
  console.log("OK minimization, groups: " + minDfa.states.length);
}

function testProperties() {
  const dfa = new Automaton({ name: "props test" });
  dfa.addState("q0");
  dfa.addState("q1");
  dfa.addState("unreachable");
  dfa.alphabet = ["a"];
  dfa.setStartState("q0");
  dfa.acceptStates = new Set(["q1"]);
  dfa.addTransition("q0", "a", "q1");
  dfa.addTransition("q1", "a", "q1");

  const report = analyzeProperties(dfa);
  assert(report.isDeterministic, "should be deterministic");
  assert(!report.isConnected, "should not be connected");
  assert(report.unreachableStates.has("unreachable"), "unreachable state must be detected");
  console.log("OK properties analysis");
}

function testSerializationRoundTrip() {
  // The .afjson format is shared with the desktop app, so it must survive
  // a full save/load cycle unchanged.
  const original = buildNfaEndsWithAb();
  const restored = Automaton.fromJSON(JSON.parse(JSON.stringify(original.toJSON())));
  assertEqual(
    JSON.stringify(restored.toJSON()),
    JSON.stringify(original.toJSON()),
    "round-trip through .afjson must be lossless"
  );
  for (const s of ["ab", "ba", "aab", ""]) {
    assertEqual(
      simulate(restored, s).accepted,
      simulate(original, s).accepted,
      'round-tripped automaton disagrees on "' + s + '"'
    );
  }
  console.log("OK .afjson round-trip");
}

function testBundledExamples() {
  // Every bundled example must load and analyse without throwing.
  const names = Object.keys(EXAMPLES);
  assert(names.length === 5, "expected 5 bundled examples, got " + names.length);
  for (const name of names) {
    const automaton = Automaton.fromJSON(EXAMPLES[name]);
    assertEqual(automaton.validate().length, 0, 'example "' + name + '" should be valid');
    analyzeProperties(automaton);
  }

  // Spot-check the semantics of two of them.
  const endsIn1 = Automaton.fromJSON(EXAMPLES["DFA: ends with 1"]);
  assert(simulate(endsIn1, "1011").accepted, '"1011" ends in 1');
  assertEqual(simulate(endsIn1, "1010").accepted, false, '"1010" does not end in 1');

  const divBy3 = Automaton.fromJSON(EXAMPLES["DFA: divisible by 3"]);
  // 110 binary = 6, divisible by 3; 111 = 7, not divisible.
  assert(simulate(divBy3, "110").accepted, "110 (=6) is divisible by 3");
  assertEqual(simulate(divBy3, "111").accepted, false, "111 (=7) is not divisible by 3");
  console.log("OK bundled examples");
}

/* ------------------------------------------------------------------ */

console.log("Running AutomataStudio algorithm tests (JavaScript port)\n");

testSimulation();
testSubsetConstruction();
testEpsilonNfa();
testMinimization();
testProperties();
testSerializationRoundTrip();
testBundledExamples();

console.log("\n" + checks + " checks, " + failures + " failures.");
if (failures === 0) console.log("All algorithm smoke tests passed.");

// Picked up by the runner to set the process exit code.
globalThis.__TEST_FAILURES__ = failures;
