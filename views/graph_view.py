"""Interactive canvas that draws the automaton: states, transitions, drag & zoom."""
from __future__ import annotations

import math
from typing import Dict, Optional, Set, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QWheelEvent
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsView

from models.automaton import EPSILON
from views.graph_items import StartArrowItem, StateItem, TransitionItem


class AutomatonGraphView(QGraphicsView):
    def __init__(self, controller, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.scene_ = QGraphicsScene(self)
        self.setScene(self.scene_)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.scale_factor = 1.0

        self._state_items: Dict[str, StateItem] = {}
        self._highlighted_states: Set[str] = set()
        self._highlighted_edge: Optional[Tuple[str, str, str]] = None
        self.dark_mode = False

        controller.model_changed.connect(self._on_model_changed)
        self.refresh()

    # ------------------------------------------------------------------
    def _on_model_changed(self) -> None:
        self.refresh()

    def set_dark_mode(self, enabled: bool) -> None:
        self.dark_mode = enabled
        self.refresh()

    def _on_node_moved(self, name: str, x: float, y: float) -> None:
        self.controller.move_state(name, x, y, record_history=False)

    def auto_layout(self) -> None:
        automaton = self.controller.automaton
        n = len(automaton.states)
        if n == 0:
            return
        radius = max(150, 60 * n)
        cx, cy = radius + 60, radius + 60
        for i, state in enumerate(automaton.states):
            angle = 2 * math.pi * i / n
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            automaton.positions[state] = (x, y)
        self.refresh()

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        automaton = self.controller.automaton
        self.scene_.clear()
        self._state_items.clear()

        missing = [s for s in automaton.states if s not in automaton.positions]
        if missing:
            n = len(automaton.states)
            radius = max(150, 55 * n)
            cx, cy = radius + 60, radius + 60
            for i, state in enumerate(automaton.states):
                if state not in automaton.positions:
                    angle = 2 * math.pi * i / max(n, 1)
                    automaton.positions[state] = (cx + radius * math.cos(angle), cy + radius * math.sin(angle))

        for state in automaton.states:
            item = StateItem(
                state,
                is_start=(state == automaton.start_state),
                is_accept=(state in automaton.accept_states),
                on_moved=self._on_node_moved,
            )
            x, y = automaton.positions.get(state, (0, 0))
            item.setPos(x, y)
            item.is_unreachable = state in automaton.get_unreachable_states()
            item.highlighted = state in self._highlighted_states
            item._apply_style()
            self.scene_.addItem(item)
            self._state_items[state] = item

        if automaton.start_state and automaton.start_state in self._state_items:
            self.scene_.addItem(StartArrowItem(self._state_items[automaton.start_state]))

        pair_labels: Dict[Tuple[str, str], list] = {}
        for src in automaton.states:
            for symbol, dests in automaton.transitions.get(src, {}).items():
                for dest in dests:
                    pair_labels.setdefault((src, dest), []).append(symbol)

        drawn_pairs = set()
        for (src, dest), symbols in pair_labels.items():
            if (src, dest) in drawn_pairs:
                continue
            drawn_pairs.add((src, dest))
            label = ", ".join(sorted(symbols))
            curvature = 0.0
            if src != dest and (dest, src) in pair_labels:
                curvature = 0.25
            edge = TransitionItem(self._state_items[src], self._state_items[dest], label, curvature)
            if self.dark_mode:
                edge.set_dark_mode(True)
            is_hl = False
            if self._highlighted_edge:
                hsrc, hsym, hdst = self._highlighted_edge
                if hsrc == src and hdst == dest and hsym in symbols:
                    is_hl = True
            edge.set_highlighted(is_hl)
            self.scene_.addItem(edge)

    # ------------------------------------------------------------------
    def highlight_states(self, states: Set[str], edge: Optional[Tuple[str, str, str]] = None) -> None:
        self._highlighted_states = set(states)
        self._highlighted_edge = edge
        self.refresh()

    def clear_highlights(self) -> None:
        self._highlighted_states = set()
        self._highlighted_edge = None
        self.refresh()

    # ------------------------------------------------------------------
    def wheelEvent(self, event: QWheelEvent) -> None:
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        new_scale = self.scale_factor * factor
        if 0.2 <= new_scale <= 4.0:
            self.scale(factor, factor)
            self.scale_factor = new_scale

    def zoom_in(self) -> None:
        self.scale(1.2, 1.2)
        self.scale_factor *= 1.2

    def zoom_out(self) -> None:
        self.scale(1 / 1.2, 1 / 1.2)
        self.scale_factor /= 1.2

    def zoom_reset(self) -> None:
        self.resetTransform()
        self.scale_factor = 1.0

    def fit_view(self) -> None:
        if self.scene_.itemsBoundingRect().isValid():
            self.fitInView(self.scene_.itemsBoundingRect().adjusted(-40, -40, 40, 40),
                            Qt.AspectRatioMode.KeepAspectRatio)
