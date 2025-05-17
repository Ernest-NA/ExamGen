from __future__ import annotations

# ⬇⬇⬇  examgen/gui/dialogs.py  ⬇⬇⬇
# (Reescrito completo: correcciones de borrado filas + centrado checkbox)

from pathlib import Path
from typing import List

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QTextOption, QIcon
from PySide6.QtWidgets import (
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
    QVBoxLayout,
    QWidget,
)

from examgen import models as m

DB_PATH: Path = Path("examgen.db")
MAX_LEN = 3000
MIN_ROWS = 4


# ---------------------------------------------------------------------------
# Tabla de opciones
# ---------------------------------------------------------------------------

class OptionTable(QTableWidget):
    HEADER = ["Opción", "Explicación", "Correcta", ""]

    def __init__(self, rows: int = MIN_ROWS, parent: QWidget | None = None):
        super().__init__(rows, 4, parent)

        self.setHorizontalHeaderLabels(self.HEADER)
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.resizeSection(2, 80)  # Correcta (fijo)
        header.resizeSection(3, 40)  # Eliminar (fijo)
        self.verticalHeader().setVisible(False)
        self.setWordWrap(True)

        self._populate_rows(initial=True)

    # ------------------------------------------------------------------
    def _populate_rows(self, initial: bool = False) -> None:
        for row in range(self.rowCount()):
            self._setup_row(row, initial)

    def _setup_row(self, row: int, initial: bool = False) -> None:
        # Checkbox centrado
        chk = QTableWidgetItem()
        chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        chk.setCheckState(Qt.CheckState.Unchecked)
        chk.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setItem(row, 2, chk)

        # Botón eliminar
        btn = QToolButton()
        btn.setIcon(QIcon.fromTheme("edit-delete"))
        btn.setAutoRaise(True)
        btn.clicked.connect(lambda _=False, r=row: self._delete_row(r))
        self.setCellWidget(row, 3, btn)

    # ------------------------------------------------------------------
    def _delete_row(self, row: int) -> None:
        if self.rowCount() > MIN_ROWS:
            self.removeRow(row)
        self._refresh_delete_buttons()

    def add_empty_row(self) -> None:
        self.insertRow(self.rowCount())
        self._setup_row(self.rowCount() - 1)
        self._refresh_delete_buttons()

    def _refresh_delete_buttons(self) -> None:
        """Enable delete on *all* rows whenever total > MIN_ROWS."""
        allow_delete = self.rowCount() > MIN_ROWS
        for r in range(self.rowCount()):
            btn = self.cellWidget(r, 3)
            if btn:
                btn.setEnabled(allow_delete)

    # ------------------------------------------------------------------
    def collect_options(self) -> tuple[List[m.AnswerOption], int]:
        opts: List[m.AnswerOption] = []
        correct = 0
        for r in range(self.rowCount()):
            opt_item = self.item(r, 0)
            if not opt_item or not opt_item.text().strip():
                continue
            text = opt_item.text().strip()[:MAX_LEN]
            expl_item = self.item(r, 1)
            expl = expl_item.text().strip()[:MAX_LEN] if expl_item else ""
            chk_item = self.item(r, 2)
            is_corr = chk_item and chk_item.checkState() == Qt.CheckState.Checked
            if is_corr:
                correct += 1
            opts.append(
                m.AnswerOption(text=text, is_correct=is_corr, meta={"explanation": expl})  # type: ignore[arg-type]
            )
        return opts, correct


# ---------------------------------------------------------------------------
# Diálogo principal (sin cambios relevantes salvo ancho ventana)
# ---------------------------------------------------------------------------

class QuestionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nueva pregunta – MCQ")
        self.resize(1920, 1080)

        # Materia
        self.subject_combo = QComboBox(editable=True)
        self._load_subjects()

        # Enunciado + contador
        self.prompt_edit = QPlainTextEdit()
        self.prompt_edit.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self.prompt_edit.textChanged.connect(self._update_counter)
        self.counter = QLabel("0/3000", alignment=Qt.AlignmentFlag.AlignRight)
        self.counter.setStyleSheet("color:#888;font-size:11px")

        # Tabla opciones + botón añadir
        self.options_table = OptionTable(MIN_ROWS, self)
        add_btn = QPushButton("+")
        add_btn.setFixedSize(QSize(30, 30))
        add_btn.clicked.connect(self.options_table.add_empty_row)

        # Layout
        form = QFormLayout()
        form.addRow("Materia:", self.subject_combo)
        form.addRow("Enunciado:", self.prompt_edit)
        form.addRow("", self.counter)
        form.addRow(QLabel("Opciones (texto, explicación, correcta):"))
        form.addRow(self.options_table)
        form.addRow(add_btn)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(buttons)

    # ------------------------------------------------------------------
    def _update_counter(self) -> None:
        txt = self.prompt_edit.toPlainText()
        if len(txt) > MAX_LEN:
            self.prompt_edit.setPlainText(txt[:MAX_LEN])
            cur = self.prompt_edit.textCursor()
            cur.movePosition(cur.End)
            self.prompt_edit.setTextCursor(cur)
        self.counter.setText(f"{len(self.prompt_edit.toPlainText())}/{MAX_LEN}")

    def _load_subjects(self) -> None:
        try:
            with m.Session(m.get_engine(DB_PATH)) as s:
                names = [sub.name for sub in s.query(m.Subject).order_by(m.Subject.name)]
        except Exception:
            names = []
        self.subject_combo.addItems(names)
        self.subject_combo.setPlaceholderText("Selecciona o escribe…")

    # ------------------------------------------------------------------
    def accept(self) -> None:  # noqa: D401
        subj = self.subject_combo.currentText().strip()
        prompt = self.prompt_edit.toPlainText().strip()[:MAX_LEN]
        if not subj or not prompt:
            QMessageBox.warning(self, "Datos incompletos", "Materia y enunciado son obligatorios.")
            return

        options, correct = self.options_table.collect_options()
        if len(options) < 2 or correct == 0:
            QMessageBox.warning(self, "Datos incompletos", "Añade al menos dos opciones y marca la(s) correcta(s).")
            return

        try:
            with m.Session(m.get_engine(DB_PATH)) as s:
                subj_obj = s.query(m.Subject).filter_by(name=subj).first() or m.Subject(name=subj)
                q = m.MCQQuestion(prompt=prompt, subject=subj_obj)
                q.options = options
                s.add(q)
                s.commit()
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))
            return

        QMessageBox.information(self, "Guardado", "Pregunta creada correctamente.")
        super().accept()
