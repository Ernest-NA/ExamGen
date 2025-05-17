from __future__ import annotations
from pathlib import Path
from typing import List

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QTextOption, QFontMetrics
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
ROW_HEIGHT = 60  # altura mínima


# -------- Delegate que elimina elipsis y permite wrap ------------------ #
class WrapDelegate(QStyledItemDelegate):
    def initStyleOption(self, option: QStyleOptionViewItem, index):  # type: ignore[override]
        super().initStyleOption(option, index)
        option.textElideMode = Qt.ElideNone
        option.features |= QStyleOptionViewItem.WrapText


# ------------------- tabla de opciones ---------------------------------- #
class OptionTable(QTableWidget):
    HEADER = ["", "Opción", "Correcta", "Respuesta", "Explicación", ""]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(MIN_ROWS, 6, parent)

        self.setWordWrap(True)
        self.setHorizontalHeaderLabels(self.HEADER)
        hdr = self.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.resizeSection(2, 80)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        hdr.resizeSection(5, 40)
        hdr.setStretchLastSection(False)

        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)

        # Delegate wrap para columnas de texto
        wrap = WrapDelegate(self)
        for col in (1, 3, 4):
            self.setItemDelegateForColumn(col, wrap)

        for r in range(MIN_ROWS):
            self._init_row(r)
        self._refresh_delete_buttons()

        # Ajustar altura al editar
        self.itemChanged.connect(self._auto_height)

    # ---------------- inicializar filas --------------------------------- #
    def _init_row(self, row: int) -> None:
        letter = QTableWidgetItem(chr(ord("a") + row))
        letter.setFlags(Qt.ItemFlag.ItemIsEnabled)
        letter.setTextAlignment(Qt.AlignCenter)
        self.setItem(row, 0, letter)

        cb = QCheckBox()
        c = QWidget()
        lay = QHBoxLayout(c)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addStretch(1)
        lay.addWidget(cb)
        lay.addStretch(1)
        self.setCellWidget(row, 2, c)

        trash = QToolButton()
        trash.setIcon(QIcon.fromTheme("edit-delete"))
        trash.setAutoRaise(True)
        trash.clicked.connect(lambda *_: self._remove_row(row))
        self.setCellWidget(row, 5, trash)

    # ---------------- añadir / borrar ----------------------------------- #
    def add_row(self) -> None:
        r = self.rowCount()
        self.insertRow(r)
        self._init_row(r)
        self._refresh_letters()
        self._refresh_delete_buttons()

    def _remove_row(self, row: int) -> None:
        if self.rowCount() > MIN_ROWS:
            self.removeRow(row)
            self._refresh_letters()
            self._refresh_delete_buttons()

    def _refresh_letters(self) -> None:
        for r in range(self.rowCount()):
            self.item(r, 0).setText(chr(ord("a") + r))

    def _refresh_delete_buttons(self) -> None:
        allow = self.rowCount() > MIN_ROWS
        for r in range(self.rowCount()):
            w = self.cellWidget(r, 5)
            btn = w if isinstance(w, QToolButton) else w.findChild(QToolButton)  # type: ignore
            btn.setEnabled(allow)

    # ---------------- auto-altura --------------------------------------- #
    def _auto_height(self, row: int) -> None:
        fm: QFontMetrics = self.fontMetrics()
        lines = 1
        for col in (1, 3, 4):
            item = self.item(row, col)
            if not item or not item.text():
                continue
            # estimar líneas según ancho de columna
            est_lines = (
                fm.horizontalAdvance(item.text()) // max(self.columnWidth(col), 1) + 1
            )
            lines = max(lines, est_lines)
        new_h = max(ROW_HEIGHT, lines * (fm.lineSpacing() + 4))
        if self.rowHeight(row) != new_h:
            self.setRowHeight(row, new_h)

    # ---------------- recoger datos ------------------------------------- #
    def collect(self) -> tuple[List[m.AnswerOption], int]:
        opts: List[m.AnswerOption] = []
        correct = 0
        for r in range(self.rowCount()):
            txt_item = self.item(r, 1)
            if txt_item is None or not txt_item.text().strip():
                continue
            text = txt_item.text().strip()[:MAX_CHARS]
            answer = (self.item(r, 3).text() if self.item(r, 3) else "").strip()[:MAX_CHARS]
            expl = (self.item(r, 4).text() if self.item(r, 4) else "").strip()[:MAX_CHARS]
            cb: QCheckBox = self.cellWidget(r, 2).findChild(QCheckBox)  # type: ignore
            is_corr = cb.isChecked()
            if is_corr:
                correct += 1
            opts.append(
                m.AnswerOption(
                    text=text,
                    is_correct=is_corr,
                    meta={"answer": answer, "explanation": expl},
                )
            )
        return opts, correct


# ------------------- diálogo principal ---------------------------------- #
class QuestionDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, *, db_path: Path = DB_PATH) -> None:
        super().__init__(parent)
        self.db_path = db_path
        self.setWindowTitle("Nueva pregunta – MCQ")
        self.resize(1920, 1080)

        # Materia & Referencia
        self.cb_subject = QComboBox(editable=True, fixedWidth=500)
        self.cb_reference = QComboBox(editable=True, fixedWidth=250)
        self._load_subjects()

        top = QHBoxLayout()
        top.addWidget(self.cb_subject)
        top.addSpacing(20)
        top.addWidget(QLabel("Referencia:"))
        top.addWidget(self.cb_reference)
        top.addStretch(1)
        w_top = QWidget()
        w_top.setLayout(top)

        # Enunciado
        self.prompt = QPlainTextEdit()
        self.prompt.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self.counter = QLabel("0/3000", alignment=Qt.AlignRight)
        self.prompt.textChanged.connect(self._update_counter)

        # Tabla y “+”
        self.table = OptionTable(self)
        add_btn = QPushButton("+")
        add_btn.setFixedSize(QSize(30, 30))
        add_btn.clicked.connect(self.table.add_row)

        # Layout
        form = QFormLayout()
        form.addRow("Materia:", w_top)
        form.addRow("Enunciado:", self.prompt)
        form.addRow("", self.counter)
        form.addRow(QLabel("Opciones (texto, explicación, correcta):"))
        form.addRow(self.table)
        h = QHBoxLayout()
        h.addWidget(add_btn)
        h.addStretch(1)
        form.addRow(h)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(buttons)

    # ---- helpers -------------------------------------------------------- #
    def _update_counter(self) -> None:
        txt = self.prompt.toPlainText()
        if len(txt) > MAX_CHARS:
            self.prompt.setPlainText(txt[:MAX_CHARS])
            self.prompt.moveCursor(self.prompt.textCursor().End)
        self.counter.setText(f"{len(self.prompt.toPlainText())}/3000")

    def _load_subjects(self) -> None:
        with m.Session(m.get_engine(self.db_path)) as s:
            names = sorted(sub.name for sub in s.query(m.Subject).all())
        self.cb_subject.addItems(names)
        self.cb_reference.addItems(names)
        self.cb_subject.setPlaceholderText("Seleccione / escriba…")
        self.cb_reference.setPlaceholderText("Seleccione / escriba…")

    # ---- guardar -------------------------------------------------------- #
    def accept(self) -> None:  # noqa: D401
        subj = self.cb_subject.currentText().strip()
        ref = self.cb_reference.currentText().strip()
        prompt_txt = self.prompt.toPlainText().strip()

        if not subj or not prompt_txt:
            QMessageBox.warning(self, "Datos incompletos", "Materia y enunciado obligatorios.")
            return

        options, correct = self.table.collect()
        if len(options) < 2 or correct == 0:
            QMessageBox.warning(self, "Datos incompletos", "Añade ≥2 opciones y marca la(s) correcta(s).")
            return

        with m.Session(m.get_engine(self.db_path)) as s:
            subj_obj = s.query(m.Subject).filter_by(name=subj).first() or m.Subject(name=subj)
            ref_obj = s.query(m.Subject).filter_by(name=ref).first() if ref else None
            q = m.MCQQuestion(prompt=prompt_txt, subject=subj_obj, reference=ref_obj)  # type: ignore[arg-type]
            q.options = options
            s.add
