"""End-to-end smoke test driving the real GUI code paths headlessly."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtWidgets import QApplication

from views.main_window import MainWindow
from resources.examples import EXAMPLES

app = QApplication(sys.argv)
w = MainWindow()
w.show()
app.processEvents()

# 1. Load NFA example, simulate a string, step through it.
w._load_example("AFND: contiene 'ab'")
app.processEvents()
assert len(w.controller.automaton.states) == 3

w.simulation_panel.input_line.setText("bbab")
w.simulation_panel._run_simulation()
app.processEvents()
assert w.simulation_panel._result.accepted, "expected 'bbab' to be accepted"
w.simulation_panel._step_next()
w.simulation_panel._toggle_autoplay()
app.processEvents()
w.simulation_panel._toggle_autoplay()
print("OK simulation + stepping")

# 2. Convert NFA -> DFA, apply, verify determinism.
conv_panel = w.analysis_tabs.widget(1)
conv_panel._convert()
app.processEvents()
assert conv_panel._result is not None
conv_panel._apply()
app.processEvents()
assert w.controller.automaton.is_deterministic()
print("OK NFA->DFA conversion + apply, states:", w.controller.automaton.states)

# 3. Minimize the resulting DFA.
min_panel = w.analysis_tabs.widget(2)
min_panel._minimize()
app.processEvents()
assert min_panel._result is not None
min_panel._apply()
app.processEvents()
print("OK minimization + apply, states:", w.controller.automaton.states)

# 4. DFA -> NFA (trivial wrap).
nfa_panel = w.analysis_tabs.widget(3)
nfa_panel._convert()
nfa_panel._apply()
app.processEvents()
print("OK DFA->NFA conversion + apply")

# 5. Editor panel operations: add state, symbol, transition, undo/redo.
w.controller.new_automaton()
w.controller.add_state("q0")
w.controller.add_state("q1")
w.controller.add_symbol("0")
w.controller.add_symbol("1")
w.controller.add_transition("q0", "0", "q1")
w.controller.toggle_accept_state("q1")
app.processEvents()
assert w.controller.automaton.states == ["q0", "q1"]
w.controller.undo()
app.processEvents()
assert "q1" not in w.controller.automaton.accept_states
w.controller.redo()
app.processEvents()
assert "q1" in w.controller.automaton.accept_states
print("OK editor mutations + undo/redo")

# 6. Drag a state (simulate itemChange callback) and confirm position persists w/o exploding.
from views.graph_items import StateItem
item = w.graph_view._state_items.get("q0")
assert item is not None
item.setPos(123, 456)
app.processEvents()
assert w.controller.automaton.positions["q0"] == (123, 456)
print("OK drag/move persistence")

# 7. Properties analysis on example with dead/unreachable states.
w._load_example("AFD: con estados muertos e inaccesibles")
app.processEvents()
report = w.controller.analyze_properties()
assert "C" in report.unreachable_states or "E" in report.unreachable_states
print("OK properties analysis, unreachable:", report.unreachable_states, "dead:", report.dead_states)

# 8. Save / load project round-trip.
import tempfile, os
with tempfile.TemporaryDirectory() as tmp:
    path = os.path.join(tmp, "test.afjson")
    w.current_file_path = path
    w._write_project(path)
    assert os.path.exists(path)
    from utils import file_io
    loaded = file_io.load_project(path)
    assert loaded.states == w.controller.automaton.states
    print("OK save/load project round-trip")

    # 9. Export PNG + PDF.
    png_path = os.path.join(tmp, "out.png")
    file_io.export_scene_png(w.graph_view.scene_, png_path)
    assert os.path.exists(png_path) and os.path.getsize(png_path) > 0
    print("OK PNG export, size:", os.path.getsize(png_path))

    pdf_path = os.path.join(tmp, "out.pdf")
    file_io.export_pdf(pdf_path, w.controller.automaton, png_path,
                        [("Cadena", "101"), ("Resultado", "Aceptada")],
                        ["Determinista: Sí", "Completo: No"])
    assert os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0
    print("OK PDF export, size:", os.path.getsize(pdf_path))

# 10. Dark mode toggle.
w.act_dark_mode.setChecked(True)
app.processEvents()
w.act_dark_mode.setChecked(False)
app.processEvents()
print("OK dark mode toggle")

# 11. Zoom controls.
w.graph_view.zoom_in()
w.graph_view.zoom_out()
w.graph_view.zoom_reset()
w.graph_view.fit_view()
w.graph_view.auto_layout()
app.processEvents()
print("OK zoom + layout controls")

print("\nAll GUI smoke tests passed.")
