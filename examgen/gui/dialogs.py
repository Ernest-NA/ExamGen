from __future__ import annotations
from pathlib import Path
from typing import List

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QTextOption
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


# -------------- Delegate que envuelve texto en cualquier punto ---------- #
class WrapAnywhereDelegate(QStyledItemDelegate):
    _flags = Qt.TextWordWrap | Qt.TextWrapAnywhere

    def initStyleOption(self, option: QStyleOptionViewItem, index):  # type: ignore[override]
        super().initStyleOption(option, index)
        option.textElideMode = Qt.ElideNone
        option.displayAlignment = Qt.AlignLeft | Qt.AlignVCenter

    def sizeHint(self, option: QStyleOptionViewItem, index):  # type: ignore[override]
        # Qt calculará bien el alto con wrap; aquí solo respetamos mínimo
        size = super().sizeHint(option, index)
        min_h = option.fontMetrics.lineSpacing() + 6
        if size.height() < min_h:
            size.setHeight(min_h)
        return size

    def paint(self, painter, option, index):  # type: ignore[override]
        self.initStyleOption(option, index)
        painter.save()
        painter.drawText(option.rect, self._flags, str(index.data(Qt.DisplayRole)))
        painter.restore()


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
        min_h = self.fontMetrics().lineSpacing() + 6
        self.verticalHeader().setDefaultSectionSize(min_h)

        wrap = WrapAnywhereDelegate(self)
        for col in (1, 3, 4):
            self.setItemDelegateForColumn(col, wrap)

        for r in range(MIN_ROWS):
            self._init_row(r)
        self._refresh_delete_buttons()
        self.resizeRowsToContents()

        self.cellChanged.connect(self._auto_height)

    # ---------------- inicializar filas --------------------------------- #
    def _init_row(self, row: int) -> None:
        # Letra
        letter = QTableWidgetItem(chr(ord("a") + row))
        letter.setFlags(Qt.ItemFlag.ItemIsEnabled)
        letter.setTextAlignment(Qt.AlignCenter)
        self.setItem(row, 0, letter)

        # Columnas de texto vacías (sin “None”)
        for col in (1, 3, 4):
            self.setItem(row, col, QTableWidgetItem(""))

        # Checkbox
        chk = QCheckBox()
        box = QWidget()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addStretch(1)
        lay.addWidget(chk)
        lay.addStretch(1)
        self.setCellWidget(row, 2, box)

        # Papelera
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
        self.resizeRowsToContents()

    def _remove_row(self, row: int) -> None:
        if self.rowCount() > MIN_ROWS:
            self.removeRow(row)
            self._refresh_letters()
            self._refresh_delete_buttons()
            self.resizeRowsToContents()

    def _refresh_letters(self) -> None:
        for r in range(self.rowCount()):
            self.item(r, 0).setText(chr(ord("a") + r))

    def _refresh_delete_buttons(self) -> None:
        allow = self.rowCount() > MIN_ROWS
        for r in range(self.rowCount()):
            btn: QToolButton | None = self.cellWidget(r, 5).findChild(QToolButton)  # type: ignore
            if btn:
                btn.setEnabled(allow)
    
    # ---------------- auto-altura -------------------------------------- #
    def _auto_height(self, row: int, _col: int) -> None:
        """Ajusta la altura de *row* al alto real del texto (sin límite)."""
        fm    = self.fontMetrics()
        flags = Qt.TextWrapAnywhere          # envuelve incluso sin espacios
        min_h = fm.lineSpacing() + 6         # altura mínima
        height = min_h

        for col in (1, 3, 4):                # columnas con texto
            item = self.item(row, col)
            if not item:
                continue
            width = max(self.columnWidth(col) - 4, 1)
            rect  = fm.boundingRect(0, 0, width, 10_000, flags, item.text())
            height = max(height, rect.height() + 6)

        if self.rowHeight(row) != height:
            self.setRowHeight(row, height)

    # ---------------- recoger datos ------------------------------------- #
    def collect(self) -> tuple[List[m.AnswerOption], int]:
        opts: List[m.AnswerOption] = []
        correct = 0
        for r in range(self.rowCount()):
            text = self.item(r, 1).text().strip()  # type: ignore[attribute-defined-outside-init]
            if not text:
                continue
            text = text[:MAX_CHARS]
            answer = self.item(r, 3).text().strip()[:MAX_CHARS]   # type: ignore
            expl = self.item(r, 4).text().strip()[:MAX_CHARS]     # type: ignore
            is_corr = self.cellWidget(r, 2).findChild(QCheckBox).isChecked()  # type: ignore
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
        top.setContentsMargins(0, 0, 0, 0) 
        top.addWidget(self.cb_subject)
        top.addSpacing(20)
        top.addWidget(QLabel("Referencia:"))
        top.addWidget(self.cb_reference)
        top.addStretch(1)
        w_top = QWidget(); w_top.setLayout(top)

        # --- Enunciado -------------------------------------------------------
        self.prompt = QPlainTextEdit()
        self.prompt.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self.counter = QLabel("0/3000", alignment=Qt.AlignRight)
        self.prompt.textChanged.connect(self._update_counter)

        w_prompt = QWidget()                 # NUEVO contenedor sin margen
        hp      = QHBoxLayout(w_prompt)
        hp.setContentsMargins(0, 0, 0, 0)    # ← sin separación
        hp.addWidget(self.prompt)

        # Tabla y botón +
        self.table = OptionTable(self)
        add_btn = QPushButton("+", clicked=self.table.add_row, fixedSize=QSize(30, 30))

        # Layout
        form = QFormLayout()
        form.addRow("Materia:", w_top)
        form.addRow("Enunciado:", w_prompt)
        form.addRow("", self.counter)
        form.addRow(QLabel("Opciones (texto, explicación, correcta):"))
        form.addRow(self.table)
        h = QHBoxLayout(); h.addWidget(add_btn); h.addStretch(1)
        form.addRow(h)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel,
                                   accepted=self.accept, rejected=self.reject)

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
            QMessageBox.warning(
                self, "Datos incompletos", "Añade ≥2 opciones y marca la(s) correcta(s)."
            )
            return

        with m.Session(m.get_engine(self.db_path)) as s:
            subj_obj = s.query(m.Subject).filter_by(name=subj).first() or m.Subject(name=subj)
            ref_obj = s.query
