from __future__ import annotations
from pathlib import Path
from typing import List

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QTextOption
from PySide6.QtWidgets import QLineEdit  # añade al import
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QHeaderView,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QStyledItemDelegate,
    QStyleOptionViewItem,
)

from examgen import models as m

DB_PATH = Path("examgen.db")
MAX_CHARS = 3000
MIN_ROWS = 4

# ------------------------------------------------------------------
# Delegate that wraps text even without spaces
# ------------------------------------------------------------------
class WrapAnywhereDelegate(QStyledItemDelegate):
    _flags = Qt.TextWordWrap | Qt.TextWrapAnywhere

    def initStyleOption(self, option: QStyleOptionViewItem, index):  # type: ignore[override]
        super().initStyleOption(option, index)
        option.textElideMode = Qt.ElideNone
        option.displayAlignment = Qt.AlignLeft | Qt.AlignVCenter

    def sizeHint(self, option: QStyleOptionViewItem, index):  # type: ignore[override]
        size = super().sizeHint(option, index)
        min_h = option.fontMetrics.lineSpacing() + 6
        size.setHeight(max(size.height(), min_h))
        return size

    def paint(self, painter, option, index):  # type: ignore[override]
        self.initStyleOption(option, index)
        painter.save()
        painter.drawText(option.rect, self._flags, str(index.data(Qt.DisplayRole) or ""))
        painter.restore()

# ------------------------------------------------------------------
# OptionTable
# ------------------------------------------------------------------
class OptionTable(QTableWidget):
    HEADER = ["", "Opción", "Correcta", "Respuesta", "Explicación", ""]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(MIN_ROWS, 6, parent)

        # header setup
        self.setHorizontalHeaderLabels(self.HEADER)
        hh = self.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.resizeSection(2, 80)
        hh.setSectionResizeMode(3, QHeaderView.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.Stretch)
        hh.resizeSection(5, 40)
        hh.setStretchLastSection(False)

        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(self.fontMetrics().lineSpacing() + 6)
        self.setWordWrap(True)

        wrap = WrapAnywhereDelegate(self)
        for c in (1, 3, 4):
            self.setItemDelegateForColumn(c, wrap)

        for r in range(MIN_ROWS):
            self._init_row(r)
        self._refresh_delete_buttons()
        self.resizeRowsToContents()

        self.cellChanged.connect(self._auto_height)

    # ------------ row helpers -----------------
    def _init_row(self, row: int):
        letter = QTableWidgetItem(chr(ord("a") + row))
        letter.setFlags(Qt.ItemIsEnabled)
        letter.setTextAlignment(Qt.AlignCenter)
        self.setItem(row, 0, letter)

        for col in (1, 3, 4):
            self.setItem(row, col, QTableWidgetItem(""))

        cb = QCheckBox()
        wrap = QWidget()
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addStretch(1)
        lay.addWidget(cb)
        lay.addStretch(1)
        self.setCellWidget(row, 2, wrap)

        trash = QToolButton()
        trash.setIcon(QIcon.fromTheme("edit-delete"))
        trash.setAutoRaise(True)
        trash.clicked.connect(lambda *_: self._remove_row(row))
        self.setCellWidget(row, 5, trash)

    def add_row(self):
        r = self.rowCount()
        self.insertRow(r)
        self._init_row(r)
        self._refresh_letters()
        self._refresh_delete_buttons()
        self.resizeRowsToContents()

    def _remove_row(self, row: int):
        if self.rowCount() > MIN_ROWS:
            self.removeRow(row)
            self._refresh_letters()
            self._refresh_delete_buttons()
            self.resizeRowsToContents()

    def _refresh_letters(self):
        for r in range(self.rowCount()):
            self.item(r, 0).setText(chr(ord("a") + r))

    def _refresh_delete_buttons(self):
        allow = self.rowCount() > MIN_ROWS
        for r in range(self.rowCount()):
            btn: QToolButton | None = self.cellWidget(r, 5).findChild(QToolButton)  # type: ignore
            if btn:
                btn.setEnabled(allow)

    def _auto_height(self, row: int, _col: int):
        self.resizeRowToContents(row)

    # ------------ collect ---------------------
    def collect(self) -> tuple[List[m.AnswerOption], int]:
        opts: List[m.AnswerOption] = []
        correct = 0
        for r in range(self.rowCount()):
            text = self.item(r, 1).text().strip()
            if not text:
                continue
            text = text[:MAX_CHARS]
            answer = self.item(r, 3).text().strip()[:MAX_CHARS]
            expl   = self.item(r, 4).text().strip()[:MAX_CHARS]
            is_corr = self.cellWidget(r, 2).findChild(QCheckBox).isChecked()  # type: ignore
            if is_corr:
                correct += 1
            opts.append(
                m.AnswerOption(
                    text=text,
                    answer=answer or None,
                    explanation=expl or None,
                    is_correct=is_corr,
                )
            )
        return opts, correct

# ------------------------------------------------------------------
# QuestionDialog
# ------------------------------------------------------------------
class QuestionDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, *, db_path: Path = DB_PATH):
        super().__init__(parent)
        self.db_path = db_path
        self.setWindowTitle("Nueva pregunta – MCQ")
        self.resize(1920, 1080)

        # subject / reference
        self.cb_subject = QComboBox(editable=True, fixedWidth=500)
        self.le_reference = QLineEdit()
        self.le_reference.setPlaceholderText("ej.: exam_1025")

        top = QHBoxLayout(); top.setContentsMargins(0, 0, 0, 0)
        top.addWidget(self.cb_subject)
        top.addSpacing(20)
        top.addWidget(QLabel("Referencia:"))
        top.addWidget(self.le_reference)
        w_top = QWidget(); w_top.setLayout(top)
        

        # prompt
        self.prompt = QPlainTextEdit()
        self.prompt.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self.counter = QLabel("0/3000", alignment=Qt.AlignRight)
        self.prompt.textChanged.connect(self._update_counter)

        w_prompt = QWidget(); hp = QHBoxLayout(w_prompt); hp.setContentsMargins(0, 0, 0, 0); hp.addWidget(self.prompt)

        # table options
        self.table = OptionTable(self)
        add_btn = QPushButton("+", clicked=self.table.add_row, fixedSize=QSize(30, 30))

        form = QFormLayout()
        form.addRow("Materia:", w_top)
        form.addRow("Enunciado:", w_prompt)
        form.addRow("", self.counter)
        form.addRow(QLabel("Opciones (texto, explicación, correcta):"))
        form.addRow(self.table)
        h = QHBoxLayout(); h.addWidget(add_btn); h.addStretch(1)
        form.addRow(h)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(buttons)
        self._load_subjects()

    # ---------------- helpers -----------------
    def _update_counter(self):
        txt = self.prompt.toPlainText()
        if len(txt) > MAX_CHARS:
            self.prompt.setPlainText(txt[:MAX_CHARS])
            self.prompt.moveCursor(self.prompt.textCursor().End)
        self.counter.setText(f"{len(self.prompt.toPlainText())}/{MAX_CHARS}")

    def _load_subjects(self):
        """Carga materias existentes en el combo de materia."""
        with m.Session(m.get_engine(self.db_path)) as s:
            names = sorted(sub.name for sub in s.query(m.Subject).all())
        self.cb_subject.addItems(names)
        self.cb_subject.setPlaceholderText("Seleccione / escriba…")

    # ---------------- guardar -----------------
    def accept(self):  # type: ignore[override]  noqa: D401
        subj = self.cb_subject.currentText().strip()
        ref = self.le_reference.text().strip() 
        prompt_txt = self.prompt.toPlainText().strip()

        if not subj or not prompt_txt:
            QMessageBox.warning(self, "Datos incompletos", "Materia y enunciado obligatorios.")
            return

        options, correct = self.table.collect()
        if len(options) < 2 or correct == 0:
            QMessageBox.warning(self, "Datos incompletos", "Añade ≥2 opciones y marca la(s) correcta(s).")
            return

        engine = m.get_engine(self.db_path)
        with m.Session(engine) as s:
            subj_obj = s.query(m.Subject).filter_by(name=subj).first() or m.Subject(name=subj)
            ref_obj  = s.query(m.Subject).filter_by(name=ref).first() if ref else None

            q = m.MCQQuestion(
                prompt=prompt_txt,
                subject=subj_obj,
                reference=ref or None,
            )
            q.options = options
            s.add(q)
            s.commit()

        QMessageBox.information(self, "Pregunta guardada", "La pregunta se ha almacenado correctamente.")
        super().accept()
