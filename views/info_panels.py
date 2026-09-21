"""Right-side analysis panels: properties, NFA->DFA, minimization, DFA->NFA."""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class PropertiesPanel(QWidget):
    def __init__(self, controller, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        layout = QVBoxLayout(self)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        layout.addWidget(self.text)
        controller.model_changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        report = self.controller.analyze_properties()
        lines = [
            f"<b>¿Es determinista (AFD)?</b> {'Sí' if report.is_deterministic else 'No'}",
            f"<b>¿Es completo?</b> {'Sí' if report.is_complete else 'No'}",
            f"<b>¿Es conexo?</b> {'Sí' if report.is_connected else 'No'}",
            f"<b>¿Tiene transiciones épsilon?</b> {'Sí' if report.has_epsilon_transitions else 'No'}",
            f"<b>Estados inaccesibles:</b> {', '.join(sorted(report.unreachable_states)) or 'ninguno'}",
            f"<b>Estados muertos:</b> {', '.join(sorted(report.dead_states)) or 'ninguno'}",
        ]
        if report.missing_transitions:
            lines.append("<b>Transiciones faltantes (no completo):</b>")
            lines.append("<br>".join(report.missing_transitions[:30]))
        if report.validation_errors:
            lines.append("<b style='color:#c94f4f;'>Errores de validación:</b>")
            lines.append("<br>".join(report.validation_errors))
        self.text.setHtml("<br>".join(lines))


class ConversionPanel(QWidget):
    """AFND -> AFD via subset construction, with a step-by-step table."""

    def __init__(self, controller, main_window, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.main_window = main_window
        self._result = None
        layout = QVBoxLayout(self)

        self.btn_convert = QPushButton("Convertir AFND → AFD (construcción por subconjuntos)")
        layout.addWidget(self.btn_convert)

        self.table = QTableWidget(0, 1)
        layout.addWidget(QLabel("Tabla de subconjuntos"))
        layout.addWidget(self.table)

        row = QHBoxLayout()
        self.btn_apply = QPushButton("Usar como autómata actual")
        self.btn_apply.setEnabled(False)
        row.addWidget(self.btn_apply)
        layout.addLayout(row)

        self.btn_convert.clicked.connect(self._convert)
        self.btn_apply.clicked.connect(self._apply)

    def _convert(self) -> None:
        try:
            result = self.controller.convert_nfa_to_dfa()
        except ValueError as e:
            QMessageBox.warning(self, "No se pudo convertir", str(e))
            return
        self._result = result
        alphabet = result.dfa.alphabet
        headers = ["Estado AFD", "Subconjunto AFND"] + alphabet
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(result.steps))
        for i, step in enumerate(result.steps):
            self.table.setItem(i, 0, QTableWidgetItem(step.dfa_state))
            self.table.setItem(i, 1, QTableWidgetItem("{" + ",".join(sorted(step.source_nfa_states)) + "}"))
            for j, symbol in enumerate(alphabet):
                self.table.setItem(i, 2 + j, QTableWidgetItem(step.transitions.get(symbol, "-")))
        self.table.resizeColumnsToContents()
        self.btn_apply.setEnabled(True)
        self.main_window.show_status(
            f"AFD generado con {len(result.dfa.states)} estados a partir de {len(self.controller.automaton.states)} estados del AFND."
        )

    def _apply(self) -> None:
        if self._result:
            self.controller.replace_automaton(self._result.dfa)
            self.main_window.show_status("Autómata reemplazado por el AFD equivalente.")


class MinimizationPanel(QWidget):
    def __init__(self, controller, main_window, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.main_window = main_window
        self._result = None
        layout = QVBoxLayout(self)

        self.btn_minimize = QPushButton("Minimizar AFD")
        layout.addWidget(self.btn_minimize)

        self.text = QTextEdit()
        self.text.setReadOnly(True)
        layout.addWidget(QLabel("Particiones por iteración"))
        layout.addWidget(self.text)

        self.btn_apply = QPushButton("Usar como autómata actual")
        self.btn_apply.setEnabled(False)
        layout.addWidget(self.btn_apply)

        self.btn_minimize.clicked.connect(self._minimize)
        self.btn_apply.clicked.connect(self._apply)

    def _minimize(self) -> None:
        try:
            result = self.controller.minimize()
        except ValueError as e:
            QMessageBox.warning(self, "No se pudo minimizar", str(e))
            return
        self._result = result
        lines = []
        if result.removed_unreachable:
            lines.append(f"Estados inaccesibles eliminados antes de minimizar: {', '.join(sorted(result.removed_unreachable))}")
        for step in result.steps:
            groups = " | ".join("{" + ",".join(sorted(g)) + "}" for g in step.groups)
            lines.append(f"<b>{step.description}</b><br>{groups}")
        lines.append(f"<br><b>Resultado:</b> {len(result.dfa.states)} estados en el AFD mínimo.")
        self.text.setHtml("<br><br>".join(lines))
        self.btn_apply.setEnabled(True)
        self.main_window.show_status(f"AFD minimizado a {len(result.dfa.states)} estados.")

    def _apply(self) -> None:
        if self._result:
            self.controller.replace_automaton(self._result.dfa)
            self.main_window.show_status("Autómata reemplazado por el AFD mínimo.")


class DfaToNfaPanel(QWidget):
    def __init__(self, controller, main_window, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.main_window = main_window
        self._result = None
        layout = QVBoxLayout(self)

        info = QLabel(
            "Todo AFD es también un AFND válido (un AFD es un caso particular de AFND).\n"
            "Esta acción genera una copia del autómata actual marcada como AFND equivalente."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.btn_convert = QPushButton("Generar AFND equivalente")
        layout.addWidget(self.btn_convert)

        self.btn_apply = QPushButton("Usar como autómata actual")
        self.btn_apply.setEnabled(False)
        layout.addWidget(self.btn_apply)
        layout.addStretch(1)

        self.btn_convert.clicked.connect(self._convert)
        self.btn_apply.clicked.connect(self._apply)

    def _convert(self) -> None:
        self._result = self.controller.convert_dfa_to_nfa()
        self.btn_apply.setEnabled(True)
        self.main_window.show_status("AFND equivalente generado.")

    def _apply(self) -> None:
        if self._result:
            self.controller.replace_automaton(self._result)
            self.main_window.show_status("Autómata reemplazado por el AFND equivalente.")


class HistoryPanel(QWidget):
    """Shows the most recent simulations and conversions performed."""

    def __init__(self, controller, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Últimas simulaciones"))
        self.sim_text = QTextEdit()
        self.sim_text.setReadOnly(True)
        layout.addWidget(self.sim_text)
        layout.addWidget(QLabel("Últimas conversiones"))
        self.conv_text = QTextEdit()
        self.conv_text.setReadOnly(True)
        layout.addWidget(self.conv_text)

    def refresh(self) -> None:
        sim_lines = []
        for result in self.controller.simulation_log[:10]:
            verdict = "ACEPTADA" if result.accepted else "RECHAZADA"
            text = result.input_string or "(cadena vacía)"
            sim_lines.append(f"'{text}' → {verdict}")
        self.sim_text.setPlainText("\n".join(sim_lines) or "Sin simulaciones todavía.")
        self.conv_text.setPlainText("\n".join(self.controller.conversion_log[:10]) or "Sin conversiones todavía.")


class AnalysisTabs(QTabWidget):
    def __init__(self, controller, main_window, parent=None) -> None:
        super().__init__(parent)
        self.addTab(PropertiesPanel(controller), "Propiedades")
        self.addTab(ConversionPanel(controller, main_window), "AFND → AFD")
        self.addTab(MinimizationPanel(controller, main_window), "Minimizar AFD")
        self.addTab(DfaToNfaPanel(controller, main_window), "AFD → AFND")
        self.history_panel = HistoryPanel(controller)
        self.addTab(self.history_panel, "Historial")
