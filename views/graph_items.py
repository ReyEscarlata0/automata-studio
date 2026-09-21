"""QGraphicsItem subclasses used to draw automaton states and transitions."""
from __future__ import annotations

import math
from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsSimpleTextItem,
    QStyleOptionGraphicsItem,
    QWidget,
)

STATE_RADIUS = 28
ARROW_SIZE = 10

COLOR_NORMAL = QColor("#4a90d9")
COLOR_ACCEPT = QColor("#2e9e5b")
COLOR_START_RING = QColor("#e08a1e")
COLOR_HIGHLIGHT = QColor("#e0483e")
COLOR_HIGHLIGHT_TEXT = QColor("#ffffff")
COLOR_DEAD = QColor("#8a8f98")
COLOR_UNREACHABLE_BORDER = QColor("#c94f4f")


def _arrow_head(tip: QPointF, angle_rad: float) -> QPolygonF:
    p1 = tip
    p2 = tip - QPointF(math.cos(angle_rad - math.pi / 7) * ARROW_SIZE,
                        math.sin(angle_rad - math.pi / 7) * ARROW_SIZE)
    p3 = tip - QPointF(math.cos(angle_rad + math.pi / 7) * ARROW_SIZE,
                        math.sin(angle_rad + math.pi / 7) * ARROW_SIZE)
    return QPolygonF([p1, p2, p3])


class StateItem(QGraphicsEllipseItem):
    def __init__(self, name: str, is_start: bool, is_accept: bool, on_moved=None) -> None:
        super().__init__(-STATE_RADIUS, -STATE_RADIUS, STATE_RADIUS * 2, STATE_RADIUS * 2)
        self.name = name
        self.is_start = is_start
        self.is_accept = is_accept
        self.is_dead = False
        self.is_unreachable = False
        self.highlighted = False
        self.on_moved = on_moved
        self.edges: list = []

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setZValue(2)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        self.label = QGraphicsSimpleTextItem(name, self)
        font = QFont()
        font.setBold(True)
        font.setPointSize(9)
        self.label.setFont(font)
        self._center_label()
        self._apply_style()

    def _center_label(self) -> None:
        rect = self.label.boundingRect()
        self.label.setPos(-rect.width() / 2, -rect.height() / 2)

    def _apply_style(self) -> None:
        if self.highlighted:
            fill = COLOR_HIGHLIGHT
            text_color = COLOR_HIGHLIGHT_TEXT
        elif self.is_dead:
            fill = COLOR_DEAD
            text_color = QColor("#ffffff")
        elif self.is_accept:
            fill = COLOR_ACCEPT
            text_color = QColor("#ffffff")
        else:
            fill = COLOR_NORMAL
            text_color = QColor("#ffffff")

        pen = QPen(COLOR_START_RING if self.is_start else QColor("#1c1e21"))
        pen.setWidth(3 if self.is_start else 2)
        if self.is_unreachable:
            pen.setColor(COLOR_UNREACHABLE_BORDER)
            pen.setStyle(Qt.PenStyle.DashLine)
        self.setPen(pen)
        self.setBrush(QBrush(fill))
        self.label.setBrush(QBrush(text_color))

    def set_highlighted(self, value: bool) -> None:
        self.highlighted = value
        self._apply_style()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self.edges:
                edge.update_path()
            if self.on_moved:
                self.on_moved(self.name, self.pos().x(), self.pos().y())
        return super().itemChange(change, value)

    def boundingRect(self) -> QRectF:
        pad = 8
        return super().boundingRect().adjusted(-pad, -pad, pad, pad)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None) -> None:
        super().paint(painter, option, widget)
        if self.is_accept:
            painter.setPen(self.pen())
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QRectF(-STATE_RADIUS + 5, -STATE_RADIUS + 5,
                                        (STATE_RADIUS - 5) * 2, (STATE_RADIUS - 5) * 2))


class TransitionItem(QGraphicsPathItem):
    def __init__(self, source: StateItem, target: StateItem, label: str, curvature: float = 0.0) -> None:
        super().__init__()
        self.source = source
        self.target = target
        self.curvature = curvature
        self.highlighted = False
        self.dark_mode = False
        self.setZValue(1)
        self.setPen(QPen(QColor("#5c6470"), 2))

        self.label_item = QGraphicsSimpleTextItem(label, self)
        font = QFont()
        font.setPointSize(9)
        self.label_item.setFont(font)
        self.label_item.setBrush(QBrush(QColor("#333844")))

        source.edges.append(self)
        target.edges.append(self)
        self.update_path()

    def set_label(self, label: str) -> None:
        self.label_item.setText(label)
        self.update_path()

    def set_dark_mode(self, enabled: bool) -> None:
        self.dark_mode = enabled
        if not self.highlighted:
            self._apply_normal_style()

    def _apply_normal_style(self) -> None:
        line_color = QColor("#aab2c0") if self.dark_mode else QColor("#5c6470")
        text_color = QColor("#e6e6e6") if self.dark_mode else QColor("#333844")
        self.setPen(QPen(line_color, 2))
        self.label_item.setBrush(QBrush(text_color))

    def set_highlighted(self, value: bool) -> None:
        self.highlighted = value
        if value:
            self.setPen(QPen(COLOR_HIGHLIGHT, 3))
            self.label_item.setBrush(QBrush(COLOR_HIGHLIGHT))
        else:
            self._apply_normal_style()

    def update_path(self) -> None:
        path = QPainterPath()
        if self.source is self.target:
            cx, cy = self.source.pos().x(), self.source.pos().y()
            loop_rect = QRectF(cx - 22, cy - STATE_RADIUS - 45, 44, 45)
            path.moveTo(cx - 14, cy - STATE_RADIUS + 4)
            path.cubicTo(
                QPointF(cx - 30, cy - STATE_RADIUS - 40),
                QPointF(cx + 30, cy - STATE_RADIUS - 40),
                QPointF(cx + 14, cy - STATE_RADIUS + 4),
            )
            self.setPath(path)
            arrow = _arrow_head(QPointF(cx + 14, cy - STATE_RADIUS + 4), math.radians(60))
            self._arrow_polygon = arrow
            self.label_item.setPos(cx - self.label_item.boundingRect().width() / 2, cy - STATE_RADIUS - 62)
            self.update()
            return

        sp = self.source.pos()
        tp = self.target.pos()
        dx, dy = tp.x() - sp.x(), tp.y() - sp.y()
        dist = math.hypot(dx, dy) or 1
        ux, uy = dx / dist, dy / dist
        start = QPointF(sp.x() + ux * STATE_RADIUS, sp.y() + uy * STATE_RADIUS)
        end = QPointF(tp.x() - ux * STATE_RADIUS, tp.y() - uy * STATE_RADIUS)

        mid = QPointF((start.x() + end.x()) / 2, (start.y() + end.y()) / 2)
        # perpendicular offset for curvature (used when two states have edges both ways)
        perp = QPointF(-uy, ux) * (dist * self.curvature)
        ctrl = mid + perp

        path.moveTo(start)
        if self.curvature:
            path.quadTo(ctrl, end)
            angle = math.atan2(end.y() - ctrl.y(), end.x() - ctrl.x())
        else:
            path.lineTo(end)
            angle = math.atan2(dy, dx)
        self.setPath(path)
        self._arrow_polygon = _arrow_head(end, angle)

        label_pos = ctrl if self.curvature else mid
        self.label_item.setPos(label_pos.x() - self.label_item.boundingRect().width() / 2,
                                label_pos.y() - 18)
        self.update()

    def boundingRect(self) -> QRectF:
        return super().boundingRect().adjusted(-15, -60, 15, 15)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None) -> None:
        super().paint(painter, option, widget)
        if hasattr(self, "_arrow_polygon"):
            painter.setBrush(QBrush(self.pen().color()))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPolygon(self._arrow_polygon)


class StartArrowItem(QGraphicsPathItem):
    """A short arrow pointing into the start state, with no source node."""

    def __init__(self, target: StateItem) -> None:
        super().__init__()
        self.target = target
        self.setZValue(1)
        self.setPen(QPen(QColor("#e08a1e"), 2))
        target.edges.append(self)
        self.update_path()

    def update_path(self) -> None:
        tp = self.target.pos()
        start = QPointF(tp.x() - STATE_RADIUS - 40, tp.y())
        end = QPointF(tp.x() - STATE_RADIUS, tp.y())
        path = QPainterPath()
        path.moveTo(start)
        path.lineTo(end)
        self.setPath(path)
        self._arrow_polygon = _arrow_head(end, 0)
        self.update()

    def boundingRect(self) -> QRectF:
        return super().boundingRect().adjusted(-15, -15, 15, 15)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None) -> None:
        super().paint(painter, option, widget)
        if hasattr(self, "_arrow_polygon"):
            painter.setBrush(QBrush(self.pen().color()))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPolygon(self._arrow_polygon)
