"""Bottom panel: string simulation with step-by-step playback."""
from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from algorithms.simulation import SimulationResult
from utils.validators import validate_input_string


class SimulationPanel(QWidget):
    def __init__(self, controller, graph_view, main_window, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.graph_view = graph_view
        self.main_window = main_window
        self._result: Optional[SimulationResult] = None
        self._step_index = 0

        self._timer = QTimer(self)
        self._timer.setInterval(800)
        self._timer.timeout.connect(self._advance_auto)

        layout = QVBoxLayout(self)
        input_row = QHBoxLayout()
        input_row.addWidget(QLabel("Cadena a simular:"))
        self.input_line = QLineEdit()
        self.input_line.returnPressed.connect(self._run_simulation)
        input_row.addWidget(self.input_line, 1)
        self.btn_run = QPushButton("Simular")
        self.btn_run.clicked.connect(self._run_simulation)
        input_row.addWidget(self.btn_run)
        layout.addLayout(input_row)

        controls_row = QHBoxLayout()
        self.btn_reset = QPushButton("⏮ Reiniciar")
        self.btn_prev = QPushButton("◀ Anterior")
        self.btn_next = QPushButton("Siguiente ▶")
        self.btn_play = QPushButton("▶ Auto")
        for b in (self.btn_reset, self.btn_prev, self.btn_next, self.btn_play):
            b.setObjectName("secondary")
            b.setEnabled(False)
            controls_row.addWidget(b)
        self.result_label = QLabel("")
        self.result_label.setStyleSheet("font-weight: bold; padding-left: 12px;")
        controls_row.addWidget(self.result_label, 1, Qt.AlignmentFlag.AlignRight)
        layout.addLayout(controls_row)

        self.btn_reset.clicked.connect(self._reset_playback)
        self.btn_prev.clicked.connect(self._step_prev)
        self.btn_next.clicked.connect(self._step_next)
        self.btn_play.clicked.connect(self._toggle_autoplay)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Paso", "Símbolo", "Estado(s) actual(es)", "Estado(s) siguiente(s)"])
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

    # ------------------------------------------------------------------
    def _run_simulation(self) -> None:
        text = self.input_line.text()
        error = validate_input_string(text, self.controller.automaton)
        if error:
            QMessageBox.warning(self, "Cadena inválida", error)
            return
        result = self.controller.simulate_string(text)
        self._result = result
        self._step_index = 0
        self._populate_table(result)
        self.main_window.refresh_history_panel()

        for b in (self.btn_reset, self.btn_prev, self.btn_next, self.btn_play):
            b.setEnabled(True)

        if result.error:
            self.result_label.setText(result.error)
            self.result_label.setStyleSheet("font-weight: bold; color: #c94f4f; padding-left: 12px;")
        elif result.accepted:
            self.result_label.setText("✔ CADENA ACEPTADA")
            self.result_label.setStyleSheet("font-weight: bold; color: #2e9e5b; padding-left: 12px;")
        else:
            self.result_label.setText("✘ CADENA RECHAZADA")
            self.result_label.setStyleSheet("font-weight: bold; color: #c94f4f; padding-left: 12px;")

        self._show_step(0)

    def _populate_table(self, result: SimulationResult) -> None:
        self.table.setRowCount(len(result.steps))
        for i, step in enumerate(result.steps):
            self.table.setItem(i, 0, QTableWidgetItem(str(step.index)))
            self.table.setItem(i, 1, QTableWidgetItem(step.symbol or "(inicio)"))
            self.table.setItem(i, 2, QTableWidgetItem("{" + ",".join(sorted(step.from_states)) + "}" if step.from_states else "-"))
            self.table.setItem(i, 3, QTableWidgetItem("{" + ",".join(sorted(step.to_states)) + "}"))
        self.table.resizeColumnsToContents()

    # ------------------------------------------------------------------
    def _show_step(self, index: int) -> None:
        if not self._result or not self._result.steps:
            return
        index = max(0, min(index, len(self._result.steps) - 1))
        self._step_index = index
        step = self._result.steps[index]
        self.table.selectRow(index)
        edge = None
        if step.symbol and step.from_states:
            src = next(iter(step.from_states), None)
            for target in step.to_states:
                edge = (src, step.symbol, target)
                break
        self.graph_view.highlight_states(step.to_states, edge)

    def _reset_playback(self) -> None:
        self._timer.stop()
        self.btn_play.setText("▶ Auto")
        self._show_step(0)

    def _step_prev(self) -> None:
        self._show_step(self._step_index - 1)

    def _step_next(self) -> None:
        self._show_step(self._step_index + 1)

    def _advance_auto(self) -> None:
        if self._result and self._step_index >= len(self._result.steps) - 1:
            self._timer.stop()
            self.btn_play.setText("▶ Auto")
            return
        self._step_next()

    def _toggle_autoplay(self) -> None:
        if self._timer.isActive():
            self._timer.stop()
            self.btn_play.setText("▶ Auto")
        else:
            self._timer.start()
            self.btn_play.setText("⏸ Pausa")

    def clear(self) -> None:
        self._timer.stop()
        self._result = None
        self.table.setRowCount(0)
        self.result_label.setText("")
        self.graph_view.clear_highlights()
        for b in (self.btn_reset, self.btn_prev, self.btn_next, self.btn_play):
            b.setEnabled(False)
