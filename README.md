# AutomataStudio

**Build, simulate and analyse finite automata — in your browser or on your desktop.**

An educational tool for creating, editing, converting, simulating and analysing
Deterministic (DFA) and Non-deterministic (NFA) Finite Automata, including
ε-transitions. It exists in two forms that share the same file format and the
same algorithms: a **web app** that runs entirely in the browser, and a
**Python desktop app** built with PyQt6.

[![Live demo](https://img.shields.io/badge/live%20demo-open-2d6fd6)](https://reyescarlata0.github.io/automata-studio/)
[![Deploy](https://github.com/ReyEscarlata0/automata-studio/actions/workflows/deploy-pages.yml/badge.svg)](https://github.com/ReyEscarlata0/automata-studio/actions/workflows/deploy-pages.yml)
[![Release](https://img.shields.io/github/v/release/ReyEscarlata0/automata-studio)](https://github.com/ReyEscarlata0/automata-studio/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

> 🌐 **Try it now — no installation:** **[reyescarlata0.github.io/automata-studio](https://reyescarlata0.github.io/automata-studio/)**
>
> 💻 **Prefer a desktop app?** [Download AutomataStudio.exe](https://github.com/ReyEscarlata0/automata-studio/releases/latest) (Windows, no Python needed)

*[Versión en español del README](README.es.md)*

---

## Features

**Editing**
- Visual editor for states, alphabet and transitions, with ε-transitions
- Interactive canvas: drag states, zoom with the scroll wheel, pan, circular auto-layout
- Accepting states, start state, renaming, undo/redo
- Live validation with clear error messages

**Simulation**
- Step-by-step simulation of any automaton, DFA or NFA alike, by tracking the
  set of active states
- Active states and the edges just taken are highlighted on the diagram
- Walk forward and backward through the run, or play it automatically
- Input tape showing exactly which symbol is being consumed

**Analysis and conversion**
- **NFA → DFA** by subset construction, with the full subset table
- **DFA minimization** by partition refinement (Moore), shown iteration by iteration
- **DFA → NFA** equivalent view
- Property report: deterministic, complete, connected, ε-transitions,
  unreachable states, dead states and missing transitions

**Files**
- Save and open `.afjson` projects — **the same file works in both apps**
- Export the diagram to PNG
- Printable report (diagram, properties and transition table) that the browser
  can save as PDF; the desktop app writes the PDF directly

**Interface**
- Light and dark themes, following the system preference by default
- Responsive layout that works on tablets and phones
- The web app is fully static: no server, no account, nothing leaves your machine

---

## The two versions

|  | Web app | Desktop app |
|---|---|---|
| Run it | [In the browser](https://reyescarlata0.github.io/automata-studio/) | [Download the `.exe`](https://github.com/ReyEscarlata0/automata-studio/releases/latest) |
| Requirements | Any modern browser | Windows (or Python 3.10+ from source) |
| Language | JavaScript (no framework, no build step) | Python 3.10+ / PyQt6 |
| Diagram | Inline SVG | `QGraphicsView` |
| PDF report | Browser print dialog | Generated with `reportlab` |
| Source | [`web/`](web/) | repository root |

Both implement the same algorithms and read and write the same `.afjson`
format, so you can start an automaton in one and finish it in the other.

---

## Tech stack

**Web app** — vanilla JavaScript (ES2020), inline SVG, CSS custom properties.
No framework, no bundler, no dependencies: the browser loads five plain scripts
and runs them.

**Desktop app** — Python 3.10+, [PyQt6](https://pypi.org/project/PyQt6/) for
the interface, [reportlab](https://pypi.org/project/reportlab/) for PDF export,
and [PyInstaller](https://pyinstaller.org/) to produce the standalone `.exe`.

**CI/CD** — GitHub Actions runs the algorithm test suite on every push and
deploys `web/` to GitHub Pages only if the tests pass.

---

## Project structure

```
automata-studio/
├── main.py                  # Desktop entry point
├── requirements.txt
├── models/automaton.py      # Automaton data model (DFA and NFA in one class)
├── algorithms/              # Simulation, subset construction, minimization, properties
├── controllers/             # Mediator between model, algorithms and views (undo/redo)
├── views/                   # Main window, editor panels, graphics canvas
├── utils/                   # Validators, history, import/export, themes
├── resources/               # Preloaded examples and the app icon
├── tests/                   # Python smoke tests (algorithms and GUI)
├── examples/                # Sample .afjson automata, readable by both apps
└── web/                     # The browser version
    ├── index.html
    ├── css/styles.css
    ├── js/
    │   ├── automaton.js     # Port of models/automaton.py
    │   ├── algorithms.js    # Port of the algorithms/ package
    │   ├── examples.js      # Port of resources/examples.py
    │   ├── graph.js         # SVG renderer: drag, zoom, pan, edge routing
    │   └── app.js           # UI wiring, history, file I/O, export
    └── tests/               # Node test suite mirroring the Python one
```

The algorithm layer is deliberately pure in both languages: it takes an
automaton and returns a result carrying the intermediate steps, with no
dependency on Qt or on the DOM. That is what made porting the logic to
JavaScript straightforward, and it is why the two suites can be compared
case for case.

---

## Running locally

### Web app

It is a static site, so any HTTP server works:

```bash
git clone https://github.com/ReyEscarlata0/automata-studio.git
cd automata-studio/web
python -m http.server 8000
# open http://localhost:8000
```

Opening `web/index.html` directly from the file system also works — there are
no modules or fetch calls that would trip over the `file://` origin.

### Desktop app

Requires Python 3.10 or newer.

```bash
git clone https://github.com/ReyEscarlata0/automata-studio.git
cd automata-studio
pip install -r requirements.txt
python main.py
```

### Building the Windows executable

```bash
pip install pyinstaller
pyinstaller AutomataStudio.spec
# result: dist/AutomataStudio.exe
```

---

## Tests

```bash
node web/tests/run-tests.js      # JavaScript port  (45 checks)
python tests/test_algorithms.py  # Python original
python tests/smoke_gui.py        # End-to-end GUI test (needs PyQt6)
```

The two algorithm suites are deliberate mirrors of each other: same automata,
same input strings, same expected answers. Passing both is the evidence that
the port preserves the original behaviour.

---

## The `.afjson` format

A plain JSON document. `transitions` maps a state and a symbol to a **list** of
targets — that single detail is what lets one structure represent both DFAs and
NFAs. `ε` is the reserved symbol for epsilon transitions, and `positions` holds
the canvas coordinates so a diagram reopens exactly as it was arranged.

```json
{
  "name": "DFA: binary strings ending in 1",
  "states": ["q0", "q1"],
  "alphabet": ["0", "1"],
  "start_state": "q0",
  "accept_states": ["q1"],
  "transitions": {
    "q0": { "0": ["q0"], "1": ["q1"] },
    "q1": { "0": ["q0"], "1": ["q1"] }
  },
  "positions": { "q0": [100, 150], "q1": [320, 150] }
}
```

Ready-made examples live in [`examples/`](examples/): a DFA for strings ending
in `1`, a DFA for binary numbers divisible by 3, an NFA that detects the
substring `ab`, an ε-NFA for `a*b* ∪ b*a*`, and a DFA that deliberately
contains dead and unreachable states.

---

## Algorithms

| Algorithm | Implementation | Notes |
|---|---|---|
| String simulation | Active-state set + ε-closure | One routine handles DFA and NFA |
| ε-closure | Depth-first search over ε-transitions | |
| NFA → DFA | Subset construction | Records every subset it discovers |
| DFA minimization | Moore partition refinement | Drops unreachable states first |
| Reachable states | Depth-first search from the start state | |
| Dead states | Backward search from the accepting states | States that can never accept |

---

## License

[MIT](LICENSE) — free to use, modify and share, including for teaching.

Built as an educational project for an Automata Theory and Formal Languages
course.
