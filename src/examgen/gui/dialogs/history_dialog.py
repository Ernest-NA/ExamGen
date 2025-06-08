from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QMessageBox,
)

from sqlalchemy.orm import selectinload

from examgen.core import models as m
from examgen.core.models import SessionLocal


class AttemptsHistoryDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Historial de pruebas")

        cols = [
            "Materia",
            "Inicio",
            "Duración",
            "Preguntas",
            "Correctas",
            "%",
            "",
        ]
        self.table = QTableWidget(0, len(cols), self)
        self.table.setHorizontalHeaderLabels(cols)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.verticalHeader().setVisible(False)

        self._session = SessionLocal()

        self.btn_clear = QPushButton("Borrar todo")
        self.btn_close = QPushButton("Cerrar")
        self.btn_clear.clicked.connect(self._clear_all)
        self.btn_close.clicked.connect(self.reject)

        root = QVBoxLayout(self)
        root.addWidget(self.table)
        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(self.btn_clear)
        footer.addWidget(self.btn_close)
        root.addLayout(footer)

        self._reload_table()

    def _reload_table(self) -> None:
        attempts = (
            self._session.query(m.Attempt)
            .options(selectinload(m.Attempt.questions))
            .order_by(m.Attempt.started_at.desc())
            .all()
        )

        fmt = "%d/%m/%Y %H:%M"
        self.table.setRowCount(len(attempts))
        for row, at in enumerate(attempts):
            start = at.started_at.strftime(fmt) if at.started_at else "-"
            if at.ended_at:
                secs = int((at.ended_at - at.started_at).total_seconds())
                dur_txt = f"{secs//60}:{secs%60:02d} min"
            else:
                dur_txt = "-"

            total_q = len(at.questions)
            corr = at.score or 0
            pct = round((corr / total_q) * 100) if total_q else 0

            vals = [at.subject, start, dur_txt, str(total_q), str(corr), f"{pct} %"]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setFlags(Qt.ItemIsEnabled)
                if col == 0:
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)

            del_btn = QPushButton("🗑️")
            del_btn.setAutoRaise(True)  # type: ignore[attr-defined]
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.clicked.connect(lambda _, aid=at.id: self._delete_attempt(aid))
            self.table.setCellWidget(row, 6, del_btn)

        for c in range(self.table.columnCount()):
            self.table.resizeColumnToContents(c)
            w_head = self.table.horizontalHeader().sectionSizeHint(c)
            w_cells = max(self.table.sizeHintForColumn(c), w_head)
            self.table.setColumnWidth(c, w_cells + 12)

        total_w = sum(self.table.columnWidth(c) for c in range(self.table.columnCount()))
        total_w += self.table.verticalHeader().width() + 40
        self.table.setMinimumWidth(total_w)
        self.resize(total_w, self.height())

    def _delete_attempt(self, aid: int) -> None:
        if (
            QMessageBox.question(
                self,
                "Borrar examen",
                "¿Seguro que deseas borrar este examen?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            != QMessageBox.Yes
        ):
            return
        with SessionLocal() as s:
            s.query(m.Attempt).filter_by(id=aid).delete()
            s.commit()
        self._reload_table()

    def _clear_all(self) -> None:
        if (
            QMessageBox.question(
                self,
                "Borrar historial",
                "¿Seguro que deseas borrar todo el historial?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            != QMessageBox.Yes
        ):
            return
        with SessionLocal() as s:
            s.query(m.Attempt).delete()
            s.commit()
        self._reload_table()

    def reject(self) -> None:  # type: ignore[override]
        if hasattr(self, "_session"):
            self._session.close()
        super().reject()
