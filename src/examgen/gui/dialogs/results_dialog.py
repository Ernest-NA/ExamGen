from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QLabel,
    QDialog,
    QDialogButtonBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QMessageBox,
)

from sqlalchemy.orm import selectinload, joinedload

from examgen.core import models as m
from examgen.core.models import SessionLocal
from examgen.core.services.exam_service import Attempt


class ResultsDialog(QDialog):
    """Show exam results with per-question breakdown."""

    def __init__(self, attempt: Attempt, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.attempt = attempt
        self.setWindowTitle("¡Resultados del examen!")

        title = QLabel("¡Resultados del examen!", alignment=Qt.AlignCenter)
        score = attempt.score or 0
        total = len(attempt.questions)
        pct = round((score / total) * 100) if total else 0
        summary = QLabel(
            f"Puntuación: {score} / {total}   ({pct} %)",
            alignment=Qt.AlignCenter,
        )

        self.table = QTableWidget(len(attempt.questions), 4, self)
        self.table.setHorizontalHeaderLabels(["#", "Pregunta", "Tu resp.", "Correcta"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setTextElideMode(Qt.ElideRight)
        self.table.setMinimumWidth(700)

        correct_bg = QColor("#5af16a")
        correct_fg = QColor("#000000")
        wrong_bg = QColor("#ff6b6b")
        wrong_fg = QColor("#ffffff")

        for row, aq in enumerate(attempt.questions, start=0):
            qitem = QTableWidgetItem(str(row + 1))
            qitem.setFlags(Qt.ItemIsEnabled)
            qitem.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, qitem)

            prompt = aq.question.prompt
            pitem = QTableWidgetItem(prompt)
            pitem.setFlags(Qt.ItemIsEnabled)
            pitem.setToolTip(prompt)
            self.table.setItem(row, 1, pitem)

            sel_text = aq.selected_option or ""
            sitem = QTableWidgetItem(sel_text)
            sitem.setFlags(Qt.ItemIsEnabled)
            sitem.setToolTip(sel_text)
            self.table.setItem(row, 2, sitem)

            corr_text = next((o.text for o in aq.question.options if o.is_correct), "")
            citem = QTableWidgetItem(corr_text)
            citem.setFlags(Qt.ItemIsEnabled)
            citem.setToolTip(corr_text)
            self.table.setItem(row, 3, citem)

            if aq.is_correct:
                bg = correct_bg
                fg = correct_fg
            else:
                bg = wrong_bg
                fg = wrong_fg
            for c in range(4):
                cell = self.table.item(row, c)
                cell.setBackground(bg)
                cell.setForeground(fg)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, parent=self)
        buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addWidget(title)
        root.addWidget(summary)
        root.addWidget(self.table)
        root.addWidget(buttons, alignment=Qt.AlignCenter)

        self.resize(self.width() + 120, self.height())

    @classmethod
    def show_for_attempt(cls, attempt: Attempt, parent: QWidget | None = None) -> None:
        session = SessionLocal()
        attempt_db = (
            session.query(m.Attempt)
            .options(
                selectinload(m.Attempt.questions)
                .joinedload(m.AttemptQuestion.question.of_type(m.MCQQuestion))
                .selectinload(m.MCQQuestion.options)
            )
            .get(attempt.id)
        )
        if attempt_db is None:
            QMessageBox.critical(parent, "Error", "Intento no encontrado en BD")
            session.close()
            return

        dlg = cls(attempt_db, parent)
        dlg._session = session
        dlg.exec()

    def reject(self) -> None:  # type: ignore[override]
        if hasattr(self, "_session"):
            self._session.close()
        super().reject()
