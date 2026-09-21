"""Project persistence (JSON) and export (PNG / PDF) helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Tuple

from models.automaton import Automaton

PROJECT_EXTENSION = ".afjson"


def save_project(path: str, automaton: Automaton) -> None:
    data = automaton.to_dict()
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_project(path: str) -> Automaton:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return Automaton.from_dict(data)


def export_scene_png(scene, path: str, padding: int = 20) -> None:
    from PyQt6.QtCore import QRectF
    from PyQt6.QtGui import QImage, QPainter

    rect = scene.itemsBoundingRect().adjusted(-padding, -padding, padding, padding)
    if rect.isEmpty():
        rect = QRectF(0, 0, 400, 300)
    image = QImage(int(rect.width()), int(rect.height()), QImage.Format.Format_ARGB32)
    image.fill(0xFFFFFFFF)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    scene.render(painter, source=rect)
    painter.end()
    image.save(path)


def export_pdf(
    path: str,
    automaton: Automaton,
    image_path: Optional[str] = None,
    simulation_summary: Optional[List[Tuple[str, str]]] = None,
    properties_summary: Optional[List[str]] = None,
) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        Image,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(path, pagesize=A4)
    story = []

    story.append(Paragraph(f"Autómata: {automaton.name}", styles["Title"]))
    story.append(Spacer(1, 0.4 * cm))

    kind = "AFD (Determinista)" if automaton.is_deterministic() else "AFND (No determinista)"
    story.append(Paragraph(f"Tipo: {kind}", styles["Normal"]))
    story.append(Paragraph(f"Estados: {', '.join(automaton.states) or '(ninguno)'}", styles["Normal"]))
    story.append(Paragraph(f"Alfabeto: {', '.join(automaton.alphabet) or '(vacío)'}", styles["Normal"]))
    story.append(Paragraph(f"Estado inicial: {automaton.start_state or '(no definido)'}", styles["Normal"]))
    story.append(Paragraph(
        f"Estados de aceptación: {', '.join(sorted(automaton.accept_states)) or '(ninguno)'}",
        styles["Normal"],
    ))
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph("Tabla de transiciones", styles["Heading2"]))
    header = ["Estado"] + list(automaton.alphabet)
    rows = [header]
    for state in automaton.states:
        row = [state]
        for symbol in automaton.alphabet:
            targets = automaton.targets(state, symbol)
            row.append(", ".join(sorted(targets)) if targets else "-")
        rows.append(row)
    table = Table(rows, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d5f8b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.5 * cm))

    if properties_summary:
        story.append(Paragraph("Propiedades", styles["Heading2"]))
        for line in properties_summary:
            story.append(Paragraph(f"• {line}", styles["Normal"]))
        story.append(Spacer(1, 0.5 * cm))

    if image_path and Path(image_path).exists():
        story.append(Paragraph("Diagrama", styles["Heading2"]))
        story.append(Image(image_path, width=16 * cm, height=10 * cm, kind="proportional"))
        story.append(Spacer(1, 0.5 * cm))

    if simulation_summary:
        story.append(Paragraph("Resultado de simulación", styles["Heading2"]))
        for label, value in simulation_summary:
            story.append(Paragraph(f"<b>{label}:</b> {value}", styles["Normal"]))

    doc.build(story)
