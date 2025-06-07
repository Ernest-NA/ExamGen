from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QStatusBar,
    QLabel,
    QSizePolicy,
)
from PySide6.QtCore import Qt

from examgen import models as m
from examgen.models import SessionLocal
from examgen.gui.dialogs import QuestionDialog


class QuestionsWindow(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preguntas")
        if parent is not None:
            self.resize(parent.size())

        # --- fila 1: filtros + botón ---
        self.cb_subject = QComboBox()
        self.cb_subject.currentIndexChanged.connect(self._load_table)

        self.search = QLineEdit(
            placeholderText="Busca en enunciado u opciones…"
        )
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
            "Pregunta",
            "Opciones de respuesta",
            "Correcta",
            "Explicación",
            "",
        ]
        self.table = QTableWidget(0, len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
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
            q = (
                s.query(m.MCQQuestion)
                .filter(m.MCQQuestion.subject_id == subj_id)
                .order_by(m.MCQQuestion.id)
            )
            rows = q.all()

        if query_text:
            rows = [
                r
                for r in rows
                if query_text in r.prompt.lower()
                or any(query_text in o.text.lower() for o in r.options)
            ]

        self._populate_table(rows)

    def _populate_table(self, rows: list[m.MCQQuestion]) -> None:
        self.table.setRowCount(len(rows))
        for i, q in enumerate(rows, start=1):
            nitem = QTableWidgetItem(str(i))
            nitem.setFlags(Qt.ItemIsEnabled)
            nitem.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i - 1, 0, nitem)

            pitem = QTableWidgetItem(q.prompt)
            pitem.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(i - 1, 1, pitem)

            opts_txt = "\n".join(
                f"{chr(97 + j)}) {o.text}" for j, o in enumerate(q.options)
            )
            corr_txt = "\n".join(o.text for o in q.options if o.is_correct)
            expl_txt = "\n".join(o.explanation or "" for o in q.options)
            for col, txt in zip((2, 3, 4), (opts_txt, corr_txt, expl_txt)):
                item = QTableWidgetItem(txt)
                item.setFlags(Qt.ItemIsEnabled)
                self.table.setItem(i - 1, col, item)

            btn_del = QPushButton("🗑️")
            btn_del.setFlat(True)
            btn_del.clicked.connect(lambda _, qid=q.id: self._delete_question(qid))
            self.table.setCellWidget(i - 1, 5, btn_del)

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
        if dlg.exec() == dlg.Accepted:
            self._load_table()
            self._refresh_stats()

    def _delete_question(self, qid: int) -> None:
        if (
            QMessageBox.question(
                self,
                "Eliminar pregunta",
                "¿Seguro que deseas borrar esta pregunta?",
                QMessageBox.Yes | QMessageBox.No,
            )
            != QMessageBox.Yes
        ):
            return
        with SessionLocal() as s:
            s.query(m.MCQQuestion).filter_by(id=qid).delete()
            s.commit()
        self._load_table()
        self._refresh_stats()
