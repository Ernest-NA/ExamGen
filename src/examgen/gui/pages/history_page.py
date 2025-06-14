from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QToolButton,
    QMessageBox,
    QHeaderView,
    QAbstractItemView,
    QSizePolicy,
)

from sqlalchemy.orm import selectinload

from examgen.core import models as m
from examgen.core.database import SessionLocal
from examgen.gui.dialogs.results_dialog import ResultsDialog


class HistoryPage(QWidget):
    """Page displaying past exam attempts."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        cols = [
            "Materia",
            "Inicio",
            "Duración",
            "Preguntas",
            "Correctas",
            "%",
            "",
            "",
        ]
        self.table = QTableWidget(0, len(cols), self)
        self.table.setHorizontalHeaderLabels(cols)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        hh = self.table.horizontalHeader()
        icon_w = 32
        hh.resizeSection(6, icon_w)
        hh.resizeSection(7, icon_w)
        hh.setSectionResizeMode(6, QHeaderView.Fixed)
        hh.setSectionResizeMode(7, QHeaderView.Fixed)

        self.btn_clear = QPushButton("Borrar todo", clicked=self._clear_all)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        root.addWidget(self.table)
        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(self.btn_clear)
        root.addLayout(footer)

        self._reload_table()

    # ------------------------------------------------------------------
    def _reload_table(self) -> None:
        with SessionLocal() as session:
            attempts = (
                session.query(m.Attempt)
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

            vals = [
                at.subject,
                start,
                dur_txt,
                str(total_q),
                str(corr),
                f"{pct} %",
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setFlags(Qt.ItemIsEnabled)
                if col == 0:
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)

            edit_btn = QToolButton(self.table)
            edit_btn.setIcon(QIcon.fromTheme("document-preview"))
            edit_btn.setAutoRaise(True)
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.clicked.connect(lambda _, a=at: self._show_results(a))
            self.table.setCellWidget(row, 6, edit_btn)

            del_btn = QToolButton(self.table)
            del_btn.setIcon(QIcon.fromTheme("edit-delete"))
            del_btn.setAutoRaise(True)
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.clicked.connect(
                lambda _, aid=at.id: self._delete_attempt(aid)
            )
            self.table.setCellWidget(row, 7, del_btn)

        for c in range(self.table.columnCount()):
            self.table.resizeColumnToContents(c)
            w_head = self.table.horizontalHeader().sectionSizeHint(c)
            w_cells = max(self.table.sizeHintForColumn(c), w_head)
            self.table.setColumnWidth(c, w_cells + 12)

        icon_w = 32
        self.table.setColumnWidth(6, icon_w)
        self.table.setColumnWidth(7, icon_w)

        total_w = sum(
            self.table.columnWidth(c) for c in range(self.table.columnCount())
        )
        total_w += self.table.verticalHeader().width() + 40
        self.table.setMinimumWidth(total_w)
        self.resize(total_w, self.height())

    def _show_results(self, attempt: m.Attempt) -> None:
        ResultsDialog.show_for_attempt(attempt, self.window())

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
        with SessionLocal() as session:
            session.query(m.Attempt).filter_by(id=aid).delete()
            session.commit()
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
        with SessionLocal() as session:
            session.query(m.Attempt).delete()
            session.commit()
        self._reload_table()
