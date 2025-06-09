from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QStatusBar,
    QLabel,
    QSizePolicy,
)
from PySide6.QtCore import Qt

MAX_COL_W = 350  # píxeles

from examgen.core import models as m
from examgen.core.database import SessionLocal
from examgen.gui.dialogs.question_dialog import QuestionDialog
from sqlalchemy.orm import selectinload


class QuestionsWindow(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=None)
        self.setWindowTitle("Preguntas")
        self.resize(1100, 700)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # --- fila 1: filtros + botón ---
        self.cb_subject = QComboBox()
        self.cb_subject.currentIndexChanged.connect(self._load_table)

        self.search = QLineEdit(placeholderText="Busca en enunciado u opciones…")
        self.search.setEnabled(False)
        self.search.setMinimumWidth(400)
        self.search.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.search.textChanged.connect(self._filter_table)

        btn_new = QPushButton("Nueva pregunta", clicked=self._new_question)

        top = QHBoxLayout()
        top.addWidget(self.cb_subject)
        top.addWidget(self.search)
        top.addStretch(1)
        top.addWidget(btn_new)

        # --- tabla ---
        headers = [
            "No.",
            "Referencia",
            "Pregunta",
            "Sección",
            "Opciones de respuesta",
            "Correcta",
            "Explicación",
            "",
        ]
        self.table = QTableWidget(0, len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        hh = self.table.horizontalHeader()
        hh.setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(True)
        self.table.setShowGrid(True)
        self.table.setStyleSheet("QTableView::item { padding: 2px 4px; }")

        root = QVBoxLayout(self)
        # Margen izq, sup, der, inf  →  4 px de respiro arriba
        root.setContentsMargins(4, 6, 4, 0)
        root.setSpacing(4)
        root.addLayout(top)
        root.addWidget(self.table)

        self.footer = QStatusBar(self)
        self.lbl_stats = QLabel(self)
        self.footer.addWidget(self.lbl_stats)
        self.footer.setStyleSheet("QStatusBar::item { border: 0px; }")
        root.addWidget(self.footer)

        self._load_subjects()
        self._refresh_stats()

    # ---------------- loaders ----------------
    def _load_subjects(self) -> None:
        with SessionLocal() as s:
            subs = s.query(m.Subject).order_by(m.Subject.name).all()
        self.cb_subject.clear()
        self.cb_subject.addItem("--- Selecciona materia ---", None)
        for sub in subs:
            self.cb_subject.addItem(sub.name, sub.id)

    def _load_table(self) -> None:
        subj_id = self.cb_subject.currentData()
        self.search.setEnabled(bool(subj_id))
        if not subj_id:
            self.table.setRowCount(0)
            return

        query_text = self.search.text().strip().lower()

        with SessionLocal() as s:
            questions = (
                s.query(m.MCQQuestion)
                .options(selectinload(m.MCQQuestion.options))
                .filter(m.MCQQuestion.subject_id == subj_id)
                .order_by(m.MCQQuestion.id)
                .all()
            )

            if query_text:
                questions = [
                    q
                    for q in questions
                    if query_text in q.prompt.lower()
                    or any(query_text in o.text.lower() for o in q.options)
                ]

            self._populate_table(questions)

    def _populate_table(self, rows: list[m.MCQQuestion]) -> None:
        self.table.setRowCount(0)
        cur_row = 0
        for q_index, q in enumerate(rows, start=1):
            n_opts = len(q.options) or 1

            for _ in range(n_opts):
                self.table.insertRow(cur_row)

            nitem = QTableWidgetItem(str(q_index))
            nitem.setFlags(Qt.ItemIsEnabled)
            nitem.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(cur_row, 0, nitem)
            if n_opts > 1:
                self.table.setSpan(cur_row, 0, n_opts, 1)

            ref_item = QTableWidgetItem(q.reference or "")
            ref_item.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(cur_row, 1, ref_item)
            if n_opts > 1:
                self.table.setSpan(cur_row, 1, n_opts, 1)

            pitem = QTableWidgetItem(q.prompt)
            pitem.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(cur_row, 2, pitem)
            if n_opts > 1:
                self.table.setSpan(cur_row, 2, n_opts, 1)

            section_item = QTableWidgetItem(q.section or "")
            section_item.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(cur_row, 3, section_item)
            if n_opts > 1:
                self.table.setSpan(cur_row, 3, n_opts, 1)

            btn_del = QPushButton("🗑️")
            btn_del.setFlat(True)
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.setStyleSheet(
                """
                QPushButton {
                    background: transparent;
                    border: none;
                    color: #ff6b6b;
                    font-size: 16px;
                }
                QPushButton:hover {
                    color: #ffa0a0;
                }
            """
            )
            btn_del.clicked.connect(lambda _, qid=q.id: self._delete_question(qid))
            self.table.setCellWidget(cur_row, 7, btn_del)
            if n_opts > 1:
                self.table.setSpan(cur_row, 7, n_opts, 1)

            for rel_idx, opt in enumerate(q.options):
                row = cur_row + rel_idx
                self.table.setItem(
                    row, 4, QTableWidgetItem(f"{chr(97 + rel_idx)}) {opt.text}")
                )
                corr_txt = "✔" if opt.is_correct else ""
                self.table.setItem(row, 5, QTableWidgetItem(corr_txt))
                self.table.setItem(row, 6, QTableWidgetItem(opt.explanation or ""))

            cur_row += n_opts
        self._auto_resize_columns()
        self._auto_resize_rows()

    def _auto_resize_columns(self) -> None:
        """Redimensiona columnas al contenido y las limita a MAX_COL_W."""
        header = self.table.horizontalHeader()
        for c in range(self.table.columnCount()):
            self.table.resizeColumnToContents(c)
            width = self.table.columnWidth(c)
            if width > MAX_COL_W:
                self.table.setColumnWidth(c, MAX_COL_W)

    def _auto_resize_rows(self) -> None:
        """Ajusta la altura de todas las filas al contenido (sin tope)."""
        self.table.resizeRowsToContents()

    def _refresh_stats(self) -> None:
        with SessionLocal() as s:
            num_subj = s.query(m.Subject).count()
            num_q = s.query(m.MCQQuestion).count()
        self.lbl_stats.setText(f"Materias: {num_subj}   Preguntas: {num_q}")

    def _filter_table(self, _text: str) -> None:
        self._load_table()

    # ---------------- actions ----------------
    def _new_question(self) -> None:
        dlg = QuestionDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._load_table()
            self._refresh_stats()

    def _delete_question(self, qid: int) -> None:
        reply = QMessageBox.question(
            self,
            "Eliminar pregunta",
            "¿Seguro que deseas borrar esta pregunta?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        with SessionLocal() as s:
            s.query(m.MCQQuestion).filter_by(id=qid).delete()
            s.commit()
        self._load_table()
        self._refresh_stats()
