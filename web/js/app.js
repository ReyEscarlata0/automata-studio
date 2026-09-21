/**
 * Application shell: wires the editor panels, the diagram, the simulation
 * bar and the conversion tools together.
 *
 * Plays the role of views/main_window.py plus controllers/automaton_controller.py
 * in the desktop app: it is the only place that mutates the model, and every
 * mutation goes through pushHistory() so undo/redo stays consistent.
 */

(function () {
  "use strict";

  /* ---------------------------------------------------------------- */
  /* Application state                                                 */
  /* ---------------------------------------------------------------- */

  let automaton = new Automaton({ name: "Untitled automaton" });
  let graph = null;

  let undoStack = [];
  let redoStack = [];
  const HISTORY_LIMIT = 60;

  let selectedState = null;
  let selectedSymbol = null;
  let selectedTransition = null;

  let simResult = null;
  let simIndex = 0;
  let autoTimer = null;

  let pendingConversion = null;

  /* ---------------------------------------------------------------- */
  /* DOM helpers                                                       */
  /* ---------------------------------------------------------------- */

  const $ = (id) => document.getElementById(id);

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  let toastTimer = null;
  function toast(message, kind) {
    const el = $("toast");
    el.textContent = message;
    el.className = "toast show" + (kind ? " " + kind : "");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      el.className = "toast";
    }, 3200);
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function safeFilename(name) {
    const cleaned = String(name).replace(/[^A-Za-z0-9._ -]+/g, "_").trim();
    return (cleaned || "automaton").slice(0, 60);
  }

  /* ---------------------------------------------------------------- */
  /* History (undo / redo)                                             */
  /* ---------------------------------------------------------------- */

  function pushHistory() {
    undoStack.push(JSON.stringify(automaton.toJSON()));
    if (undoStack.length > HISTORY_LIMIT) undoStack.shift();
    redoStack = [];
    updateHistoryButtons();
  }

  function undo() {
    if (!undoStack.length) return;
    redoStack.push(JSON.stringify(automaton.toJSON()));
    automaton = Automaton.fromJSON(JSON.parse(undoStack.pop()));
    afterModelSwap();
  }

  function redo() {
    if (!redoStack.length) return;
    undoStack.push(JSON.stringify(automaton.toJSON()));
    automaton = Automaton.fromJSON(JSON.parse(redoStack.pop()));
    afterModelSwap();
  }

  function updateHistoryButtons() {
    $("btn-undo").disabled = undoStack.length === 0;
    $("btn-redo").disabled = redoStack.length === 0;
  }

  function afterModelSwap() {
    selectedState = null;
    selectedSymbol = null;
    selectedTransition = null;
    resetSimulation();
    graph.automaton = automaton;
    graph.selectedState = null;
    refresh();
    updateHistoryButtons();
  }

  /* ---------------------------------------------------------------- */
  /* Rendering                                                         */
  /* ---------------------------------------------------------------- */

  function refresh() {
    const report = analyzeProperties(automaton);

    // Assign diagnostics straight onto the view, then draw once.
    graph.automaton = automaton;
    graph.deadStates = report.deadStates;
    graph.unreachableStates = report.unreachableStates;
    graph.selectedState = selectedState;
    graph.render();

    renderStatesList(report);
    renderAlphabetList();
    renderTransitionSelects();
    renderTransitionsList();
    renderProperties(report);
    renderBadge();

    $("input-name").value = automaton.name;
    $("canvas-empty").hidden = automaton.states.length > 0;
    updateEditorButtons();
  }

  function renderBadge() {
    const badge = $("badge-type");
    if (!automaton.states.length) {
      badge.textContent = "—";
      badge.className = "badge";
      return;
    }
    const deterministic = automaton.isDeterministic();
    badge.textContent = deterministic ? "DFA" : "NFA";
    badge.className = "badge " + (deterministic ? "dfa" : "nfa");
  }

  function renderStatesList(report) {
    const list = $("list-states");
    list.textContent = "";
    if (!automaton.states.length) {
      list.innerHTML = '<li class="empty-note">No states yet</li>';
      return;
    }
    for (const state of automaton.states) {
      const li = document.createElement("li");
      li.dataset.state = state;
      if (state === selectedState) li.classList.add("selected");

      const tags = [];
      if (automaton.startState === state) tags.push('<span class="tag start">START</span>');
      if (automaton.acceptStates.has(state)) tags.push('<span class="tag accept">ACCEPT</span>');
      if (report.unreachableStates.has(state)) tags.push('<span class="tag unreachable">UNREACH</span>');
      if (report.deadStates.has(state)) tags.push('<span class="tag dead">DEAD</span>');

      li.innerHTML =
        "<span>" + escapeHtml(state) + "</span>" +
        '<span class="tags">' + tags.join("") + "</span>";

      li.addEventListener("click", () => {
        selectedState = state;
        graph.selectedState = state;
        graph.render();
        renderStatesList(report);
        updateEditorButtons();
      });
      list.appendChild(li);
    }
  }

  function renderAlphabetList() {
    const list = $("list-alphabet");
    list.textContent = "";
    if (!automaton.alphabet.length) {
      list.innerHTML = '<li class="empty-note">Alphabet is empty</li>';
      return;
    }
    for (const symbol of automaton.alphabet) {
      const li = document.createElement("li");
      if (symbol === selectedSymbol) li.classList.add("selected");
      li.innerHTML = "<span><code>" + escapeHtml(symbol) + "</code></span>";
      li.addEventListener("click", () => {
        selectedSymbol = symbol;
        renderAlphabetList();
        updateEditorButtons();
      });
      list.appendChild(li);
    }
  }

  function renderTransitionSelects() {
    const source = $("select-source");
    const target = $("select-target");
    const symbol = $("select-symbol");

    const prevSource = source.value;
    const prevTarget = target.value;
    const prevSymbol = symbol.value;

    const stateOptions = automaton.states
      .map((s) => '<option value="' + escapeHtml(s) + '">' + escapeHtml(s) + "</option>")
      .join("");
    source.innerHTML = stateOptions;
    target.innerHTML = stateOptions;

    symbol.innerHTML = automaton.alphabet
      .map((s) => '<option value="' + escapeHtml(s) + '">' + escapeHtml(s) + "</option>")
      .join("") + '<option value="' + EPSILON + '">' + EPSILON + " (epsilon)</option>";

    if (automaton.states.indexOf(prevSource) !== -1) source.value = prevSource;
    if (automaton.states.indexOf(prevTarget) !== -1) target.value = prevTarget;
    if (prevSymbol === EPSILON || automaton.alphabet.indexOf(prevSymbol) !== -1) {
      symbol.value = prevSymbol;
    }
  }

  function renderTransitionsList() {
    const list = $("list-transitions");
    list.textContent = "";
    const rows = automaton.allTransitionRows();
    if (!rows.length) {
      list.innerHTML = '<li class="empty-note">No transitions yet</li>';
      return;
    }
    for (const row of rows) {
      const key = row.join(KEY_SEP);
      const li = document.createElement("li");
      if (key === selectedTransition) li.classList.add("selected");
      li.innerHTML =
        "<span><code>" + escapeHtml(row[0]) + "</code> —" +
        escapeHtml(row[1]) + "→ <code>" + escapeHtml(row[2]) + "</code></span>";
      li.addEventListener("click", () => {
        selectedTransition = key;
        renderTransitionsList();
        updateEditorButtons();
      });
      list.appendChild(li);
    }
  }

  function yesNo(value) {
    return '<span class="prop-value ' + (value ? "yes" : "no") + '">' +
      (value ? "Yes" : "No") + "</span>";
  }

  function chips(states, className) {
    if (!states.size) return '<span class="hint">None</span>';
    return '<div class="state-chips">' +
      sortedArray(states)
        .map((s) => '<span class="chip ' + className + '">' + escapeHtml(s) + "</span>")
        .join("") +
      "</div>";
  }

  function renderProperties(report) {
    const body = $("properties-body");

    if (!automaton.states.length) {
      body.innerHTML = '<p class="hint">Add at least one state to see the analysis.</p>';
      return;
    }

    let html =
      '<div class="prop-row"><span class="prop-label">Deterministic (DFA)</span>' +
      yesNo(report.isDeterministic) + "</div>" +
      '<div class="prop-row"><span class="prop-label">Complete</span>' +
      yesNo(report.isComplete) + "</div>" +
      '<div class="prop-row"><span class="prop-label">Connected</span>' +
      yesNo(report.isConnected) + "</div>" +
      '<div class="prop-row"><span class="prop-label">ε-transitions</span>' +
      yesNo(report.hasEpsilonTransitions) + "</div>" +
      '<div class="prop-row"><span class="prop-label">States / symbols</span>' +
      '<span class="prop-value">' + automaton.states.length + " / " +
      automaton.alphabet.length + "</span></div>";

    html += "<h4>Unreachable states</h4>" + chips(report.unreachableStates, "bad");
    html += "<h4>Dead states</h4>" + chips(report.deadStates, "muted");

    html += "<h4>Missing transitions</h4>";
    if (!report.missingTransitions.length) {
      html += '<p class="hint">None — the automaton is complete.</p>';
    } else {
      const shown = report.missingTransitions.slice(0, 12);
      html += '<ul class="error-list" style="color:var(--text-dim)">' +
        shown.map((m) => "<li><code>" + escapeHtml(m) + "</code></li>").join("") +
        "</ul>";
      if (report.missingTransitions.length > shown.length) {
        html += '<p class="hint">…and ' +
          (report.missingTransitions.length - shown.length) + " more.</p>";
      }
    }

    if (report.validationErrors.length) {
      html += "<h4>Validation</h4><ul class=\"error-list\">" +
        report.validationErrors.map((e) => "<li>" + escapeHtml(e) + "</li>").join("") +
        "</ul>";
    } else {
      html += '<h4>Validation</h4><p class="hint" style="color:var(--ok)">The automaton is well formed.</p>';
    }

    body.innerHTML = html;
  }

  function updateEditorButtons() {
    const hasState = selectedState !== null && automaton.states.indexOf(selectedState) !== -1;
    $("btn-set-start").disabled = !hasState;
    $("btn-toggle-accept").disabled = !hasState;
    $("btn-rename-state").disabled = !hasState;
    $("btn-remove-state").disabled = !hasState;

    $("btn-remove-symbol").disabled =
      selectedSymbol === null || automaton.alphabet.indexOf(selectedSymbol) === -1;

    const rows = automaton.allTransitionRows().map((r) => r.join(KEY_SEP));
    $("btn-remove-transition").disabled =
      selectedTransition === null || rows.indexOf(selectedTransition) === -1;

    $("btn-add-transition").disabled = !automaton.states.length;
  }

  /* ---------------------------------------------------------------- */
  /* Editor actions                                                    */
  /* ---------------------------------------------------------------- */

  const STATE_NAME_RE = /^[A-Za-z0-9_-]+$/;

  function addState() {
    const input = $("input-state");
    const name = input.value.trim();
    if (!name) return toast("The state name cannot be empty.", "error");
    if (!STATE_NAME_RE.test(name)) {
      return toast("Only letters, digits, '_' and '-' are allowed.", "error");
    }
    if (automaton.states.indexOf(name) !== -1) {
      return toast('State "' + name + '" already exists.', "error");
    }

    pushHistory();
    // Drop new states near the centre of the current view.
    const rect = $("canvas").getBoundingClientRect();
    const x = (rect.width / 2 - graph.offsetX) / graph.scale + (Math.random() * 60 - 30);
    const y = (rect.height / 2 - graph.offsetY) / graph.scale + (Math.random() * 60 - 30);
    automaton.addState(name, [x, y]);
    selectedState = name;
    input.value = "";
    resetSimulation();
    refresh();
  }

  function removeState() {
    if (!selectedState) return;
    pushHistory();
    automaton.removeState(selectedState);
    selectedState = null;
    resetSimulation();
    refresh();
  }

  function renameState() {
    if (!selectedState) return;
    const next = window.prompt("New name for state " + selectedState + ":", selectedState);
    if (next === null) return;
    const name = next.trim();
    if (!name) return toast("The state name cannot be empty.", "error");
    if (!STATE_NAME_RE.test(name)) {
      return toast("Only letters, digits, '_' and '-' are allowed.", "error");
    }
    if (name !== selectedState && automaton.states.indexOf(name) !== -1) {
      return toast('State "' + name + '" already exists.', "error");
    }
    pushHistory();
    automaton.renameState(selectedState, name);
    selectedState = name;
    resetSimulation();
    refresh();
  }

  function setStartState() {
    if (!selectedState) return;
    pushHistory();
    automaton.setStartState(selectedState);
    resetSimulation();
    refresh();
  }

  function toggleAccept(state) {
    const target = state || selectedState;
    if (!target) return;
    pushHistory();
    automaton.toggleAcceptState(target);
    resetSimulation();
    refresh();
  }

  function addSymbol() {
    const input = $("input-symbol");
    const symbol = input.value.trim();
    if (!symbol) return toast("The symbol cannot be empty.", "error");
    if (symbol === EPSILON) {
      return toast("That symbol is reserved for epsilon transitions.", "error");
    }
    if (Array.from(symbol).length !== 1) {
      return toast("Use single-character symbols.", "error");
    }
    if (automaton.alphabet.indexOf(symbol) !== -1) {
      return toast('Symbol "' + symbol + '" is already in the alphabet.', "error");
    }
    pushHistory();
    automaton.addSymbol(symbol);
    input.value = "";
    resetSimulation();
    refresh();
  }

  function removeSymbol() {
    if (!selectedSymbol) return;
    pushHistory();
    automaton.removeSymbol(selectedSymbol);
    selectedSymbol = null;
    resetSimulation();
    refresh();
  }

  function addTransition() {
    const source = $("select-source").value;
    const symbol = $("select-symbol").value;
    const target = $("select-target").value;
    if (!source || !target) return toast("Create at least one state first.", "error");
    try {
      pushHistory();
      automaton.addTransition(source, symbol, target);
      resetSimulation();
      refresh();
    } catch (err) {
      undoStack.pop();
      updateHistoryButtons();
      toast(err.message, "error");
    }
  }

  function removeTransition() {
    if (!selectedTransition) return;
    const parts = selectedTransition.split(KEY_SEP);
    pushHistory();
    automaton.removeTransition(parts[0], parts[1], parts[2]);
    selectedTransition = null;
    resetSimulation();
    refresh();
  }

  /* ---------------------------------------------------------------- */
  /* Simulation                                                        */
  /* ---------------------------------------------------------------- */

  function resetSimulation() {
    stopAuto();
    simResult = null;
    simIndex = 0;
    if (graph) {
      graph.highlightedStates = new Set();
      graph.highlightedEdges = new Set();
    }
    $("sim-verdict").textContent = "";
    $("sim-verdict").className = "verdict";
    $("sim-step").textContent = "Enter a string and press Simulate.";
    $("sim-tape").textContent = "";
    setStepButtons(false);
  }

  function setStepButtons(enabled) {
    const ids = ["btn-step-first", "btn-step-prev", "btn-step-auto", "btn-step-next", "btn-step-last"];
    for (const id of ids) $(id).disabled = !enabled;
  }

  function runSimulation() {
    stopAuto();
    const input = $("input-string").value;

    const errors = automaton.validate();
    if (errors.length) {
      $("sim-verdict").textContent = "Invalid automaton";
      $("sim-verdict").className = "verdict error";
      $("sim-step").textContent = errors[0];
      setStepButtons(false);
      return;
    }

    simResult = simulate(automaton, input);
    simIndex = 0;

    if (simResult.error) {
      $("sim-verdict").textContent = "Error";
      $("sim-verdict").className = "verdict error";
      $("sim-step").textContent = simResult.error;
      graph.clearHighlight();
      setStepButtons(false);
      return;
    }

    setStepButtons(true);
    // Jump straight to the outcome, then let the user walk back through it.
    simIndex = simResult.steps.length - 1;
    renderSimStep();
  }

  function renderSimStep() {
    if (!simResult || !simResult.steps.length) return;
    const step = simResult.steps[simIndex];

    graph.setHighlight(step.toStates, step.symbol, step.fromStates);

    const consumed = simIndex;
    const symbols = Array.from(simResult.inputString);
    const tape = $("sim-tape");
    tape.textContent = "";
    if (!symbols.length) {
      const cell = document.createElement("span");
      cell.className = "cell done";
      cell.textContent = "ε (empty string)";
      tape.appendChild(cell);
    } else {
      symbols.forEach((symbol, i) => {
        const cell = document.createElement("span");
        let cls = "cell";
        if (i < consumed) cls += " done";
        else if (i === consumed) cls += " current";
        cell.className = cls;
        cell.textContent = symbol;
        tape.appendChild(cell);
      });
    }

    $("sim-step").textContent =
      "Step " + simIndex + " / " + (simResult.steps.length - 1) + " — " + step.description;

    const atEnd = simIndex === simResult.steps.length - 1;
    const verdict = $("sim-verdict");
    if (atEnd) {
      const consumedAll = simResult.steps.length - 1 === symbols.length;
      if (simResult.accepted) {
        verdict.textContent = "ACCEPTED";
        verdict.className = "verdict accepted";
      } else {
        verdict.textContent = consumedAll ? "REJECTED" : "REJECTED (stuck)";
        verdict.className = "verdict rejected";
      }
    } else {
      verdict.textContent = "running…";
      verdict.className = "verdict";
    }

    $("btn-step-prev").disabled = simIndex === 0;
    $("btn-step-first").disabled = simIndex === 0;
    $("btn-step-next").disabled = atEnd;
    $("btn-step-last").disabled = atEnd;
  }

  function goToStep(index) {
    if (!simResult) return;
    simIndex = Math.max(0, Math.min(simResult.steps.length - 1, index));
    renderSimStep();
  }

  function stopAuto() {
    if (autoTimer) {
      clearInterval(autoTimer);
      autoTimer = null;
      const btn = $("btn-step-auto");
      if (btn) btn.textContent = "▶ Auto";
    }
  }

  function toggleAuto() {
    if (autoTimer) return stopAuto();
    if (!simResult) return;
    if (simIndex >= simResult.steps.length - 1) simIndex = 0;
    $("btn-step-auto").textContent = "⏸ Pause";
    renderSimStep();
    autoTimer = setInterval(() => {
      if (!simResult || simIndex >= simResult.steps.length - 1) return stopAuto();
      simIndex += 1;
      renderSimStep();
    }, 900);
  }

  /* ---------------------------------------------------------------- */
  /* Conversions                                                       */
  /* ---------------------------------------------------------------- */

  function showConversion(html, resultAutomaton) {
    $("convert-body").innerHTML = html;
    pendingConversion = resultAutomaton || null;
    $("btn-apply-conversion").hidden = !resultAutomaton;
  }

  function conversionError(message) {
    showConversion('<p class="error-list" style="list-style:none;padding:0">' +
      escapeHtml(message) + "</p>", null);
    toast(message, "error");
  }

  function runNfaToDfa() {
    const errors = automaton.validate();
    if (errors.length) return conversionError(errors[0]);
    let result;
    try {
      result = nfaToDfa(automaton);
    } catch (err) {
      return conversionError(err.message);
    }

    const alphabet = automaton.alphabet.filter((s) => s !== EPSILON);
    let html = "<h4>Subset construction table</h4>";
    html += '<div class="table-scroll"><table><thead><tr><th>DFA state</th><th>NFA states</th>' +
      alphabet.map((s) => "<th>" + escapeHtml(s) + "</th>").join("") +
      "</tr></thead><tbody>";

    for (const step of result.steps) {
      const isStart = step.dfaState === result.dfa.startState;
      const isAccept = result.dfa.acceptStates.has(step.dfaState);
      const marks = (isStart ? "→ " : "") + (isAccept ? "* " : "");
      html += "<tr><td><code>" + escapeHtml(marks + step.dfaState) + "</code></td>" +
        "<td>{" + escapeHtml(sortedArray(step.sourceNfaStates).join(", ")) + "}</td>" +
        alphabet
          .map((s) => "<td><code>" + escapeHtml(step.transitions[s] || "∅") + "</code></td>")
          .join("") +
        "</tr>";
    }
    html += "</tbody></table></div>";
    html += '<p class="hint">→ start state · * accepting state · ' +
      result.dfa.states.length + " DFA states from " + automaton.states.length + " NFA states.</p>";

    showConversion(html, result.dfa);
    toast("Subset construction complete: " + result.dfa.states.length + " DFA states.", "ok");
  }

  function runMinimize() {
    const errors = automaton.validate();
    if (errors.length) return conversionError(errors[0]);
    let result;
    try {
      result = minimizeDfa(automaton);
    } catch (err) {
      return conversionError(err.message);
    }

    let html = "<h4>Partition refinement</h4><ol>";
    for (const step of result.steps) {
      html += "<li>" + escapeHtml(step.description) + "<br>" +
        step.groups
          .map((g) => "<code>{" + escapeHtml(sortedArray(g).join(",")) + "}</code>")
          .join(" ") +
        "</li>";
    }
    html += "</ol>";

    if (result.removedUnreachable.size) {
      html += "<h4>Removed as unreachable</h4>" +
        '<div class="state-chips">' +
        sortedArray(result.removedUnreachable)
          .map((s) => '<span class="chip bad">' + escapeHtml(s) + "</span>")
          .join("") +
        "</div>";
    }

    html += '<p class="hint">' + automaton.states.length + " states → " +
      result.dfa.states.length + " states in the minimal DFA.</p>";

    showConversion(html, result.dfa);
    toast("Minimized: " + automaton.states.length + " → " + result.dfa.states.length + " states.", "ok");
  }

  function runDfaToNfa() {
    const result = dfaToNfa(automaton);
    showConversion(
      '<p class="hint">Every DFA is already a valid NFA. This produces an equivalent copy ' +
      "labelled as an NFA, ready to extend with non-deterministic or ε-transitions.</p>",
      result
    );
  }

  function applyConversion() {
    if (!pendingConversion) return;
    pushHistory();
    automaton = pendingConversion;
    pendingConversion = null;
    $("btn-apply-conversion").hidden = true;
    $("convert-body").innerHTML = '<p class="hint">Applied. The diagram now shows the result.</p>';
    selectedState = null;
    selectedTransition = null;
    resetSimulation();
    graph.automaton = automaton;
    // Conversions invent new state names with no coordinates: lay them out.
    automaton.positions = {};
    refresh();
    graph.autoLayout();
    toast("Result applied as the current automaton.", "ok");
  }

  /* ---------------------------------------------------------------- */
  /* Files                                                             */
  /* ---------------------------------------------------------------- */

  function newAutomaton() {
    if (automaton.states.length && !window.confirm("Discard the current automaton?")) return;
    pushHistory();
    automaton = new Automaton({ name: "Untitled automaton" });
    afterModelSwap();
    toast("New empty automaton.", "ok");
  }

  function saveFile() {
    const data = JSON.stringify(automaton.toJSON(), null, 2);
    downloadBlob(new Blob([data], { type: "application/json" }),
      safeFilename(automaton.name) + ".afjson");
    toast("Downloaded as .afjson — the desktop app opens this file.", "ok");
  }

  function openFile(file) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const data = JSON.parse(String(reader.result));
        if (!data || !Array.isArray(data.states)) {
          throw new Error("This file is not a valid .afjson automaton.");
        }
        pushHistory();
        automaton = Automaton.fromJSON(data);
        afterModelSwap();
        graph.fitView();
        toast('Loaded "' + automaton.name + '".', "ok");
      } catch (err) {
        toast("Could not read the file: " + err.message, "error");
      }
    };
    reader.onerror = () => toast("Could not read the file.", "error");
    reader.readAsText(file);
  }

  function exportPng() {
    if (!automaton.states.length) return toast("Nothing to export yet.", "error");
    const background = isDark() ? "#14161a" : "#ffffff";
    graph
      .toPngBlob(background, 2)
      .then((blob) => {
        downloadBlob(blob, safeFilename(automaton.name) + ".png");
        toast("Diagram exported as PNG.", "ok");
      })
      .catch((err) => toast(err.message, "error"));
  }

  /** Opens a print-ready report; the browser's print dialog saves it as PDF. */
  function exportReport() {
    if (!automaton.states.length) return toast("Nothing to report yet.", "error");
    const report = analyzeProperties(automaton);
    const svg = graph.toStandaloneSvg("#ffffff");

    const rows = automaton
      .allTransitionRows()
      .map(
        (r) =>
          "<tr><td>" + escapeHtml(r[0]) + "</td><td>" + escapeHtml(r[1]) +
          "</td><td>" + escapeHtml(r[2]) + "</td></tr>"
      )
      .join("");

    const propRow = (label, value) =>
      "<tr><td>" + label + "</td><td><strong>" + (value ? "Yes" : "No") + "</strong></td></tr>";

    const html =
      "<!DOCTYPE html><html><head><meta charset='utf-8'><title>" +
      escapeHtml(automaton.name) + " — report</title><style>" +
      "body{font:13px/1.6 system-ui,sans-serif;color:#1c1e21;max-width:820px;margin:32px auto;padding:0 20px}" +
      "h1{font-size:20px;margin:0 0 4px}h2{font-size:14px;margin:26px 0 8px;text-transform:uppercase;" +
      "letter-spacing:.05em;color:#656d78;border-bottom:1px solid #dfe3e8;padding-bottom:4px}" +
      "table{border-collapse:collapse;width:100%;font-size:12px}" +
      "th,td{border:1px solid #dfe3e8;padding:5px 8px;text-align:left}th{background:#f4f6f8}" +
      "figure{margin:0;text-align:center}svg{max-width:100%;height:auto}" +
      ".meta{color:#656d78;font-size:12px;margin:0 0 18px}" +
      "@media print{body{margin:0}}</style></head><body>" +
      "<h1>" + escapeHtml(automaton.name) + "</h1>" +
      "<p class='meta'>" + (report.isDeterministic ? "DFA" : "NFA") + " · " +
      automaton.states.length + " states · alphabet {" +
      escapeHtml(automaton.alphabet.join(", ")) + "} · generated by AutomataStudio</p>" +
      "<h2>Diagram</h2><figure>" + svg + "</figure>" +
      "<h2>Properties</h2><table>" +
      propRow("Deterministic (DFA)", report.isDeterministic) +
      propRow("Complete", report.isComplete) +
      propRow("Connected", report.isConnected) +
      propRow("Has ε-transitions", report.hasEpsilonTransitions) +
      "<tr><td>Start state</td><td><strong>" +
      escapeHtml(automaton.startState || "—") + "</strong></td></tr>" +
      "<tr><td>Accepting states</td><td><strong>" +
      escapeHtml(sortedArray(automaton.acceptStates).join(", ") || "—") + "</strong></td></tr>" +
      "<tr><td>Unreachable states</td><td>" +
      escapeHtml(sortedArray(report.unreachableStates).join(", ") || "none") + "</td></tr>" +
      "<tr><td>Dead states</td><td>" +
      escapeHtml(sortedArray(report.deadStates).join(", ") || "none") + "</td></tr>" +
      "</table>" +
      "<h2>Transition table</h2><table><thead><tr><th>From</th><th>Symbol</th><th>To</th></tr></thead>" +
      "<tbody>" + rows + "</tbody></table>" +
      "</body></html>";

    const win = window.open("", "_blank");
    if (!win) return toast("Allow pop-ups to open the report.", "error");
    win.document.write(html);
    win.document.close();
    win.focus();
    setTimeout(() => win.print(), 400);
  }

  /* ---------------------------------------------------------------- */
  /* Theme                                                             */
  /* ---------------------------------------------------------------- */

  function isDark() {
    const attr = document.documentElement.getAttribute("data-theme");
    if (attr) return attr === "dark";
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  function applyTheme(dark) {
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
    $("btn-theme").textContent = dark ? "☀" : "🌙";
    graph.setDarkMode(dark);
    try {
      localStorage.setItem("automatastudio-theme", dark ? "dark" : "light");
    } catch (err) {
      /* private mode: the theme simply will not be remembered */
    }
  }

  function initTheme() {
    let stored = null;
    try {
      stored = localStorage.getItem("automatastudio-theme");
    } catch (err) {
      stored = null;
    }
    const dark = stored ? stored === "dark"
      : window.matchMedia("(prefers-color-scheme: dark)").matches;
    applyTheme(dark);
  }

  /* ---------------------------------------------------------------- */
  /* Tabs                                                              */
  /* ---------------------------------------------------------------- */

  function initTabs() {
    for (const panel of document.querySelectorAll(".panel")) {
      for (const tab of panel.querySelectorAll(".tab")) {
        tab.addEventListener("click", () => {
          panel.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
          panel.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
          tab.classList.add("active");
          const target = panel.querySelector('[data-panel="' + tab.dataset.tab + '"]');
          if (target) target.classList.add("active");
        });
      }
    }
  }

  /* ---------------------------------------------------------------- */
  /* Wiring                                                            */
  /* ---------------------------------------------------------------- */

  function initExamples() {
    const select = $("select-example");
    for (const key of Object.keys(EXAMPLES)) {
      const option = document.createElement("option");
      option.value = key;
      option.textContent = key;
      select.appendChild(option);
    }
    select.addEventListener("change", () => {
      const key = select.value;
      if (!key) return;
      pushHistory();
      automaton = Automaton.fromJSON(EXAMPLES[key]);
      afterModelSwap();
      graph.fitView();
      select.value = "";
      toast('Loaded example: "' + key + '".', "ok");
    });
  }

  function initEvents() {
    $("btn-add-state").addEventListener("click", addState);
    $("input-state").addEventListener("keydown", (e) => {
      if (e.key === "Enter") addState();
    });
    $("btn-remove-state").addEventListener("click", removeState);
    $("btn-rename-state").addEventListener("click", renameState);
    $("btn-set-start").addEventListener("click", setStartState);
    $("btn-toggle-accept").addEventListener("click", () => toggleAccept(null));

    $("btn-add-symbol").addEventListener("click", addSymbol);
    $("input-symbol").addEventListener("keydown", (e) => {
      if (e.key === "Enter") addSymbol();
    });
    $("btn-remove-symbol").addEventListener("click", removeSymbol);

    $("btn-add-transition").addEventListener("click", addTransition);
    $("btn-remove-transition").addEventListener("click", removeTransition);

    $("btn-simulate").addEventListener("click", runSimulation);
    $("input-string").addEventListener("keydown", (e) => {
      if (e.key === "Enter") runSimulation();
    });
    $("btn-step-first").addEventListener("click", () => { stopAuto(); goToStep(0); });
    $("btn-step-prev").addEventListener("click", () => { stopAuto(); goToStep(simIndex - 1); });
    $("btn-step-next").addEventListener("click", () => { stopAuto(); goToStep(simIndex + 1); });
    $("btn-step-last").addEventListener("click", () => {
      stopAuto();
      goToStep(simResult ? simResult.steps.length - 1 : 0);
    });
    $("btn-step-auto").addEventListener("click", toggleAuto);

    $("btn-to-dfa").addEventListener("click", runNfaToDfa);
    $("btn-minimize").addEventListener("click", runMinimize);
    $("btn-to-nfa").addEventListener("click", runDfaToNfa);
    $("btn-apply-conversion").addEventListener("click", applyConversion);

    $("btn-new").addEventListener("click", newAutomaton);
    $("btn-save").addEventListener("click", saveFile);
    $("btn-export-png").addEventListener("click", exportPng);
    $("btn-report").addEventListener("click", exportReport);
    $("btn-open").addEventListener("click", () => $("file-input").click());
    $("file-input").addEventListener("change", (e) => {
      const file = e.target.files && e.target.files[0];
      if (file) openFile(file);
      e.target.value = "";
    });

    $("btn-undo").addEventListener("click", undo);
    $("btn-redo").addEventListener("click", redo);

    $("btn-layout").addEventListener("click", () => graph.autoLayout());
    $("btn-fit").addEventListener("click", () => graph.fitView());
    $("btn-zoom-in").addEventListener("click", () => graph.zoomBy(1.2));
    $("btn-zoom-out").addEventListener("click", () => graph.zoomBy(1 / 1.2));

    $("btn-theme").addEventListener("click", () => applyTheme(!isDark()));
    $("btn-help").addEventListener("click", () => $("help-dialog").showModal());

    $("input-name").addEventListener("change", () => {
      automaton.name = $("input-name").value.trim() || "Untitled automaton";
    });

    document.addEventListener("keydown", (e) => {
      const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName);
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
        e.preventDefault();
        undo();
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "y") {
        e.preventDefault();
        redo();
      } else if (!typing && simResult && e.key === "ArrowLeft") {
        stopAuto();
        goToStep(simIndex - 1);
      } else if (!typing && simResult && e.key === "ArrowRight") {
        stopAuto();
        goToStep(simIndex + 1);
      }
    });

    window.addEventListener("resize", () => {
      // Keep the diagram usable when the layout reflows.
      if (automaton.states.length) graph.applyTransform();
    });
  }

  /* ---------------------------------------------------------------- */
  /* Boot                                                              */
  /* ---------------------------------------------------------------- */

  function init() {
    graph = new GraphView($("canvas"), {
      onStateMoved: () => { /* positions are mutated in place by the view */ },
      onStateSelected: (state) => {
        selectedState = state;
        refresh();
      },
      onStateDoubleClick: (state) => toggleAccept(state),
    });

    initTabs();
    initExamples();
    initEvents();
    initTheme();

    // Open on a worked example rather than an empty canvas.
    automaton = Automaton.fromJSON(EXAMPLES["DFA: ends with 1"]);
    graph.automaton = automaton;
    refresh();
    graph.fitView();
    resetSimulation();
    updateHistoryButtons();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
