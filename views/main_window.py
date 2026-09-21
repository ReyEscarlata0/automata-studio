"""Main application window: menu, toolbar, docks and central graph canvas."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QActionGroup, QIcon, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QStyle,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from controllers.automaton_controller import AutomatonController
from models.automaton import Automaton
from resources.examples import EXAMPLES
from utils import file_io, theme
from views.editor_panels import EditorTabs
from views.graph_view import AutomatonGraphView
from views.info_panels import AnalysisTabs
from views.simulation_panel import SimulationPanel

HELP_TEXT = """
<h2>Ayuda rápida — AutomataStudio</h2>
<p><b>1. Crear un autómata:</b> use el panel izquierdo (pestaña Estados) para agregar estados,
la pestaña Alfabeto para definir los símbolos, y la pestaña Transiciones para conectar estados.</p>
<p><b>2. Marcar estados:</b> seleccione un estado y use "Marcar inicial" o "Alternar aceptación".</p>
<p><b>3. Ver el autómata:</b> el panel central dibuja el autómata automáticamente. Arrastre los
estados con el mouse para reorganizarlos y use la rueda del mouse para hacer zoom.</p>
<p><b>4. Simular cadenas:</b> escriba una cadena en el panel inferior y presione "Simular". Use los
controles Anterior/Siguiente/Auto para recorrer paso a paso, con el estado activo resaltado en rojo.</p>
<p><b>5. Convertir y minimizar:</b> use el panel derecho para convertir AFND → AFD (construcción por
subconjuntos), AFD → AFND, o minimizar un AFD. Cada operación muestra el proceso paso a paso antes
de aplicarse.</p>
<p><b>6. Analizar propiedades:</b> la pestaña "Propiedades" indica si el autómata es determinista,
completo, conexo, y señala estados inaccesibles o muertos.</p>
<p><b>7. Guardar y exportar:</b> use el menú Archivo para guardar proyectos en JSON, o exportar el
diagrama como imagen PNG o como reporte PDF completo.</p>
<p><b>8. Ejemplos:</b> el menú Ejemplos incluye autómatas precargados (AFD y AFND) para practicar.</p>
"""


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AutomataStudio — Editor de Autómatas Finitos")
        self.resize(1400, 900)

        self.controller = AutomatonController()
        self.current_file_path: Optional[str] = None
        self.dark_mode = False

        self.graph_view = AutomatonGraphView(self.controller)
        self.setCentralWidget(self.graph_view)

        self.editor_tabs = EditorTabs(self.controller)
        self.left_dock = QDockWidget("Editor del autómata", self)
        self.left_dock.setWidget(self.editor_tabs)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.left_dock)

        self.analysis_tabs = AnalysisTabs(self.controller, self)
        self.right_dock = QDockWidget("Análisis y conversiones", self)
        self.right_dock.setWidget(self.analysis_tabs)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.right_dock)

        self.simulation_panel = SimulationPanel(self.controller, self.graph_view, self)
        self.bottom_dock = QDockWidget("Simulación paso a paso", self)
        self.bottom_dock.setWidget(self.simulation_panel)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.bottom_dock)

        self._build_actions()
        self._build_menu()
        self._build_toolbar()
        self.statusBar().showMessage("Listo.")

        self.controller.model_changed.connect(self._on_model_changed)
        self.controller.history_changed.connect(self._update_undo_redo_actions)
        self._update_undo_redo_actions()
        self._update_window_title()

    # ------------------------------------------------------------------
    def show_status(self, message: str, timeout: int = 5000) -> None:
        self.statusBar().showMessage(message, timeout)

    def refresh_history_panel(self) -> None:
        self.analysis_tabs.history_panel.refresh()

    def _on_model_changed(self) -> None:
        self._update_window_title()

    def _update_window_title(self) -> None:
        name = self.controller.automaton.name
        path = f" — {Path(self.current_file_path).name}" if self.current_file_path else ""
        self.setWindowTitle(f"AutomataStudio — {name}{path}")

    # ------------------------------------------------------------------
    def _build_actions(self) -> None:
        style = self.style()

        self.act_new = QAction(style.standardIcon(QStyle.StandardPixmap.SP_FileIcon), "Nuevo", self)
        self.act_new.setShortcut(QKeySequence.StandardKey.New)
        self.act_new.triggered.connect(self._new_project)

        self.act_open = QAction(style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton), "Abrir...", self)
        self.act_open.setShortcut(QKeySequence.StandardKey.Open)
        self.act_open.triggered.connect(self._open_project)

        self.act_save = QAction(style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), "Guardar", self)
        self.act_save.setShortcut(QKeySequence.StandardKey.Save)
        self.act_save.triggered.connect(self._save_project)

        self.act_save_as = QAction("Guardar como...", self)
        self.act_save_as.triggered.connect(self._save_project_as)

        self.act_export_png = QAction("Exportar imagen (PNG)...", self)
        self.act_export_png.triggered.connect(self._export_png)

        self.act_export_pdf = QAction("Exportar reporte (PDF)...", self)
        self.act_export_pdf.triggered.connect(self._export_pdf)

        self.act_exit = QAction("Salir", self)
        self.act_exit.triggered.connect(self.close)

        self.act_undo = QAction(style.standardIcon(QStyle.StandardPixmap.SP_ArrowBack), "Deshacer", self)
        self.act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.act_undo.triggered.connect(self._undo)

        self.act_redo = QAction(style.standardIcon(QStyle.StandardPixmap.SP_ArrowForward), "Rehacer", self)
        self.act_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self.act_redo.triggered.connect(self._redo)

        self.act_validate = QAction("Validar autómata", self)
        self.act_validate.triggered.connect(self._validate)

        self.act_auto_layout = QAction("Auto-organizar estados", self)
        self.act_auto_layout.triggered.connect(self.graph_view.auto_layout)

        self.act_zoom_in = QAction(style.standardIcon(QStyle.StandardPixmap.SP_ArrowUp), "Acercar", self)
        self.act_zoom_in.setShortcut(QKeySequence.StandardKey.ZoomIn)
        self.act_zoom_in.triggered.connect(self.graph_view.zoom_in)

        self.act_zoom_out = QAction(style.standardIcon(QStyle.StandardPixmap.SP_ArrowDown), "Alejar", self)
        self.act_zoom_out.setShortcut(QKeySequence.StandardKey.ZoomOut)
        self.act_zoom_out.triggered.connect(self.graph_view.zoom_out)

        self.act_zoom_reset = QAction("Restablecer zoom", self)
        self.act_zoom_reset.triggered.connect(self.graph_view.zoom_reset)

        self.act_fit_view = QAction("Ajustar a la vista", self)
        self.act_fit_view.triggered.connect(self.graph_view.fit_view)

        self.act_dark_mode = QAction("Modo oscuro", self, checkable=True)
        self.act_dark_mode.toggled.connect(self._toggle_dark_mode)

        self.act_help = QAction("Ayuda integrada", self)
        self.act_help.triggered.connect(self._show_help)

        self.act_about = QAction("Acerca de", self)
        self.act_about.triggered.connect(self._show_about)

    def _build_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&Archivo")
        file_menu.addAction(self.act_new)
        file_menu.addAction(self.act_open)
        file_menu.addAction(self.act_save)
        file_menu.addAction(self.act_save_as)
        file_menu.addSeparator()
        file_menu.addAction(self.act_export_png)
        file_menu.addAction(self.act_export_pdf)
        file_menu.addSeparator()
        file_menu.addAction(self.act_exit)

        edit_menu = menubar.addMenu("&Edición")
        edit_menu.addAction(self.act_undo)
        edit_menu.addAction(self.act_redo)

        automaton_menu = menubar.addMenu("&Autómata")
        automaton_menu.addAction(self.act_validate)
        automaton_menu.addAction(self.act_auto_layout)

        view_menu = menubar.addMenu("&Ver")
        view_menu.addAction(self.act_zoom_in)
        view_menu.addAction(self.act_zoom_out)
        view_menu.addAction(self.act_zoom_reset)
        view_menu.addAction(self.act_fit_view)
        view_menu.addSeparator()
        view_menu.addAction(self.left_dock.toggleViewAction())
        view_menu.addAction(self.right_dock.toggleViewAction())
        view_menu.addAction(self.bottom_dock.toggleViewAction())
        view_menu.addSeparator()
        view_menu.addAction(self.act_dark_mode)

        examples_menu = menubar.addMenu("Eje&mplos")
        for key in EXAMPLES:
            action = QAction(key, self)
            action.triggered.connect(lambda checked=False, k=key: self._load_example(k))
            examples_menu.addAction(action)

        help_menu = menubar.addMenu("A&yuda")
        help_menu.addAction(self.act_help)
        help_menu.addAction(self.act_about)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Principal", self)
        toolbar.setMovable(False)
        toolbar.setIconSize(toolbar.iconSize())
        self.addToolBar(toolbar)
        for action in (self.act_new, self.act_open, self.act_save):
            toolbar.addAction(action)
        toolbar.addSeparator()
        for action in (self.act_undo, self.act_redo):
            toolbar.addAction(action)
        toolbar.addSeparator()
        for action in (self.act_zoom_in, self.act_zoom_out):
            toolbar.addAction(action)
        toolbar.addSeparator()
        toolbar.addAction(self.act_auto_layout)
        toolbar.addAction(self.act_validate)
        toolbar.addSeparator()
        toolbar.addAction(self.act_dark_mode)

    # ------------------------------------------------------------------
    def _update_undo_redo_actions(self) -> None:
        self.act_undo.setEnabled(self.controller.history.can_undo())
        self.act_redo.setEnabled(self.controller.history.can_redo())

    def _undo(self) -> None:
        self.controller.undo()

    def _redo(self) -> None:
        self.controller.redo()

    # ------------------------------------------------------------------
    def _new_project(self) -> None:
        self.controller.new_automaton()
        self.current_file_path = None
        self.simulation_panel.clear()
        self._update_window_title()

    def _open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Abrir proyecto", "", "Proyectos AutomataStudio (*.afjson);;Todos los archivos (*)")
        if not path:
            return
        try:
            automaton = file_io.load_project(path)
        except Exception as e:
            QMessageBox.critical(self, "Error al abrir", f"No se pudo abrir el archivo:\n{e}")
            return
        self.controller.replace_automaton(automaton)
        self.current_file_path = path
        self.simulation_panel.clear()
        self._update_window_title()
        self.show_status(f"Proyecto cargado desde {path}")

    def _save_project(self) -> None:
        if not self.current_file_path:
            self._save_project_as()
            return
        self._write_project(self.current_file_path)

    def _save_project_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Guardar proyecto como", f"{self.controller.automaton.name}.afjson", "Proyectos AutomataStudio (*.afjson)")
        if not path:
            return
        if not path.endswith(".afjson"):
            path += ".afjson"
        self.current_file_path = path
        self._write_project(path)

    def _write_project(self, path: str) -> None:
        try:
            file_io.save_project(path, self.controller.automaton)
        except Exception as e:
            QMessageBox.critical(self, "Error al guardar", f"No se pudo guardar el archivo:\n{e}")
            return
        self._update_window_title()
        self.show_status(f"Proyecto guardado en {path}")

    def _export_png(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Exportar imagen", f"{self.controller.automaton.name}.png", "Imagen PNG (*.png)")
        if not path:
            return
        if not path.endswith(".png"):
            path += ".png"
        self.graph_view.clear_highlights()
        file_io.export_scene_png(self.graph_view.scene_, path)
        self.show_status(f"Imagen exportada a {path}")

    def _export_pdf(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Exportar reporte", f"{self.controller.automaton.name}.pdf", "Documento PDF (*.pdf)")
        if not path:
            return
        if not path.endswith(".pdf"):
            path += ".pdf"

        self.graph_view.clear_highlights()
        with tempfile.TemporaryDirectory() as tmp_dir:
            image_path = str(Path(tmp_dir) / "diagram.png")
            file_io.export_scene_png(self.graph_view.scene_, image_path)

            report = self.controller.analyze_properties()
            properties_summary = [
                f"Determinista: {'Sí' if report.is_deterministic else 'No'}",
                f"Completo: {'Sí' if report.is_complete else 'No'}",
                f"Conexo: {'Sí' if report.is_connected else 'No'}",
                f"Estados inaccesibles: {', '.join(sorted(report.unreachable_states)) or 'ninguno'}",
                f"Estados muertos: {', '.join(sorted(report.dead_states)) or 'ninguno'}",
            ]
            simulation_summary = None
            if self.controller.simulation_log:
                last = self.controller.simulation_log[0]
                simulation_summary = [
                    ("Cadena", last.input_string or "(vacía)"),
                    ("Resultado", "Aceptada" if last.accepted else "Rechazada"),
                ]
            try:
                file_io.export_pdf(path, self.controller.automaton, image_path, simulation_summary, properties_summary)
            except Exception as e:
                QMessageBox.critical(self, "Error al exportar", f"No se pudo generar el PDF:\n{e}")
                return
        self.show_status(f"Reporte PDF exportado a {path}")

    # ------------------------------------------------------------------
    def _validate(self) -> None:
        errors = self.controller.automaton.validate()
        if errors:
            QMessageBox.warning(self, "Validación", "Se encontraron problemas:\n\n" + "\n".join(f"• {e}" for e in errors))
        else:
            QMessageBox.information(self, "Validación", "El autómata es válido.")

    def _load_example(self, key: str) -> None:
        data = EXAMPLES[key]
        automaton = Automaton.from_dict(data)
        self.controller.replace_automaton(automaton)
        self.current_file_path = None
        self.simulation_panel.clear()
        self.graph_view.fit_view()
        self._update_window_title()
        self.show_status(f"Ejemplo cargado: {key}")

    def _toggle_dark_mode(self, checked: bool) -> None:
        self.dark_mode = checked
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(theme.stylesheet(checked))
        self.graph_view.set_dark_mode(checked)

    def _show_help(self) -> None:
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Ayuda")
        dialog.setTextFormat(Qt.TextFormat.RichText)
        dialog.setText(HELP_TEXT)
        dialog.exec()

    def _show_about(self) -> None:
        QMessageBox.about(
            self, "Acerca de AutomataStudio",
            "AutomataStudio\n\n"
            "Herramienta educativa para crear, editar, convertir, minimizar, "
            "simular y analizar Autómatas Finitos Deterministas (AFD) y "
            "No Deterministas (AFND).\n\n"
            "Desarrollado con Python y PyQt6.",
        )
