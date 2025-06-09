from __future__ import annotations
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QTextOption
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QRadioButton,
    QSpinBox,
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
    QCompleter,
    QLineEdit,
)

from examgen.core import models as m
from examgen.core.database import SessionLocal
from examgen.core.services.exam_service import ExamConfig
from examgen.core.models import SelectorTypeEnum

DB_PATH = Path("examgen.db")
MAX_CHARS = 3000
MIN_ROWS = 4


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
        painter.drawText(
            option.rect, self._flags, str(index.data(Qt.DisplayRole) or "")
        )
        painter.restore()


class OptionTable(QTableWidget):
    HEADER = ["", "Opción", "Correcta", "Explicación", ""]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(MIN_ROWS, 5, parent)

        self.setHorizontalHeaderLabels(self.HEADER)
        hh = self.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.resizeSection(2, 80)
        hh.setSectionResizeMode(3, QHeaderView.Stretch)
        hh.resizeSection(4, 40)
        hh.setStretchLastSection(False)

        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(
            self.fontMetrics().lineSpacing() + 6
        )
        self.setWordWrap(True)

        wrap = WrapAnywhereDelegate(self)
        for c in (1, 3):
            self.setItemDelegateForColumn(c, wrap)

        for r in range(MIN_ROWS):
            self._init_row(r)
        self._refresh_delete_buttons()
        self.resizeRowsToContents()

        self.cellChanged.connect(self._auto_height)

    def _init_row(self, row: int) -> None:
        letter = QTableWidgetItem(chr(ord("a") + row))
        letter.setFlags(Qt.ItemIsEnabled)
        letter.setTextAlignment(Qt.AlignCenter)
        self.setItem(row, 0, letter)

        for col in (1, 3):
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
        trash.clicked.connect(self._remove_clicked)
        self.setCellWidget(row, 4, trash)

    def _remove_clicked(self) -> None:
        """Slot conectado a cada papelera; elimina la fila donde vive el botón."""
        btn: QToolButton = self.sender()  # type: ignore
        if btn:
            r = self.indexAt(btn.parent().pos()).row()
            self._remove_row(r)

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
            btn: QToolButton | None = self.cellWidget(r, 4).findChild(QToolButton)
            if btn:
                btn.setEnabled(allow)

    def _auto_height(self, row: int, _col: int) -> None:
        self.resizeRowToContents(row)

    def collect(self) -> tuple[List[m.AnswerOption], int]:
        opts: List[m.AnswerOption] = []
        correct = 0
        for r in range(self.rowCount()):
            text = self.item(r, 1).text().strip()
            if not text:
                continue
            text = text[:MAX_CHARS]
            answer = None
            expl = self.item(r, 3).text().strip()[:MAX_CHARS]
            is_corr = self.cellWidget(r, 2).findChild(QCheckBox).isChecked()
            if is_corr:
                correct += 1
            opts.append(
                m.AnswerOption(
                    text=text,
                    answer=answer,
                    explanation=expl or None,
                    is_correct=is_corr,
                )
            )
        return opts, correct


class ExamConfigDialog(QDialog):
    """Dialog to configure exam parameters."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Configurar examen")
        self.config: Optional[ExamConfig] = None

        self.cb_subject = QComboBox()
        self.cb_subject.setEditable(True)
        self.spin_time = QSpinBox(minimum=1, maximum=999, value=90)
        self.spin_questions = QSpinBox(minimum=1, maximum=999, value=60)

        width = self.spin_time.sizeHint().width()
        self.spin_time.setFixedWidth(width)
        self.spin_questions.setFixedWidth(width)

        self.rb_random = QRadioButton("Aleatorio")
        self.rb_errors = QRadioButton("Errores")
        self.group = QButtonGroup(self)
        self.group.addButton(self.rb_random)
        self.group.addButton(self.rb_errors)

        radio_widget = QWidget()
        hr = QHBoxLayout(radio_widget)
        hr.setContentsMargins(0, 0, 0, 0)
        hr.addWidget(self.rb_random)
        hr.addWidget(self.rb_errors)
        hr.addStretch(1)

        form = QFormLayout()
        form.addRow("Materia:", self.cb_subject)
        form.addRow("Tiempo límite (min):", self.spin_time)
        form.addRow("Nº preguntas:", self.spin_questions)
        form.addRow("Selector:", radio_widget)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.btn_ok = self.buttons.button(QDialogButtonBox.Ok)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self.lbl_no_subjects = QLabel(
            "No hay materias disponibles. Importe preguntas primero.",
            alignment=Qt.AlignCenter,
        )
        self.lbl_no_subjects.setStyleSheet("color: gray")
        self.lbl_no_subjects.hide()

        self._update_ok_state()

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(self.lbl_no_subjects)
        root.addWidget(self.buttons)

        self._load_subjects()
        self._update_selector()

        self.cb_subject.currentTextChanged.connect(self._update_ok_state)
        self.group.buttonClicked.connect(self._update_ok_state)
        self.spin_questions.valueChanged.connect(self._update_ok_state)
        self.spin_time.valueChanged.connect(self._update_ok_state)

    def _load_subjects(self) -> None:
        with SessionLocal() as s:
            subjects = s.query(m.Subject).order_by(m.Subject.name).all()

        self.cb_subject.clear()
        for subj in subjects:
            self.cb_subject.addItem(subj.name, subj.id)

        if self.cb_subject.isEditable():
            self.cb_subject.setEditable(True)
            completer = QCompleter(self.cb_subject.model(), self)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            self.cb_subject.setCompleter(completer)
        else:
            self.cb_subject.setCompleter(None)

        no_subjects = len(subjects) == 0
        self.lbl_no_subjects.setVisible(no_subjects)
        self._update_ok_state()

    def _update_selector(self) -> None:
        self._update_ok_state()

    def _update_ok_state(self) -> None:
        has_items = self.cb_subject.count() > 0
        self.lbl_no_subjects.setVisible(not has_items)

        subject_ok = bool(self.cb_subject.currentText().strip()) and has_items
        selector_ok = self.group.checkedButton() is not None
        questions_ok = self.spin_questions.value() > 0
        time_ok = self.spin_time.value() > 0

        ok_enabled = subject_ok and selector_ok and questions_ok and time_ok
        self.btn_ok.setEnabled(ok_enabled)

    def accept(self) -> None:  # type: ignore[override]
        selector = (
            SelectorTypeEnum.ALEATORIO
            if self.rb_random.isChecked()
            else SelectorTypeEnum.ERRORES
        )
        self.config = ExamConfig(
            exam_id=0,
            subject=self.cb_subject.currentText().strip(),
            subject_id=int(self.cb_subject.currentData() or 0),
            selector_type=selector,
            num_questions=self.spin_questions.value(),
            error_threshold=None,
            time_limit=self.spin_time.value(),
        )
        super().accept()

    @classmethod
    def get_config(cls, parent: QWidget | None = None) -> Optional[ExamConfig]:
        dlg = cls(parent)
        return dlg.config if dlg.exec() == cls.Accepted else None


class QuestionDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, *, db_path: Path = DB_PATH):
        super().__init__(parent)
        self.db_path = db_path
        self.setWindowTitle("Nueva pregunta – MCQ")
        self.resize(1920, 1080)

        self.cb_subject = QComboBox(editable=True, fixedWidth=500)
        self.cb_section = QComboBox()
        self.cb_section.setEditable(True)
        self.cb_section.setFixedWidth(500)
        self.le_reference = QLineEdit()
        self.le_reference.setPlaceholderText("ej.: exam_1025")

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.addWidget(self.cb_subject)
        top.addSpacing(20)
        top.addWidget(QLabel("Sección:"))
        top.addWidget(self.cb_section)
        top.addSpacing(20)
        top.addWidget(QLabel("Referencia:"))
        top.addWidget(self.le_reference)
        w_top = QWidget()
        w_top.setLayout(top)

        self.prompt = QPlainTextEdit()
        self.prompt.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self.counter = QLabel("0/3000", alignment=Qt.AlignRight)
        self.prompt.textChanged.connect(self._update_counter)

        w_prompt = QWidget()
        hp = QHBoxLayout(w_prompt)
        hp.setContentsMargins(0, 0, 0, 0)
        hp.addWidget(self.prompt)

        self.table = OptionTable(self)
        add_btn = QPushButton("+", clicked=self.table.add_row, fixedSize=QSize(30, 30))

        form = QFormLayout()
        form.addRow("Materia:", w_top)
        form.addRow("Enunciado:", w_prompt)
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
        self._load_subjects()
        self._load_sections()

    def _update_counter(self) -> None:
        txt = self.prompt.toPlainText()
        if len(txt) > MAX_CHARS:
            self.prompt.setPlainText(txt[:MAX_CHARS])
            self.prompt.moveCursor(self.prompt.textCursor().End)
        self.counter.setText(f"{len(self.prompt.toPlainText())}/{MAX_CHARS}")

    def _load_subjects(self) -> None:
        with SessionLocal() as s:
            names = sorted(sub.name for sub in s.query(m.Subject).all())
        self.cb_subject.addItems(names)
        self.cb_subject.setPlaceholderText("Seleccione / escriba…")

    def _load_sections(self) -> None:
        with SessionLocal() as s:
            sections = (
                s.query(m.MCQQuestion.section)
                .filter(m.MCQQuestion.section.is_not(None))
                .distinct()
                .order_by(m.MCQQuestion.section)
                .all()
            )

        self.cb_section.clear()
        self.cb_section.addItems([sec[0] for sec in sections])

        completer = QCompleter(self.cb_section.model(), self)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.cb_section.setCompleter(completer)

    def accept(self) -> None:  # type: ignore[override]
        subj = self.cb_subject.currentText().strip()
        ref = self.le_reference.text().strip()
        section = self.cb_section.currentText().strip()
        prompt_txt = self.prompt.toPlainText().strip()

        if not subj or not prompt_txt:
            QMessageBox.warning(
                self, "Datos incompletos", "Materia y enunciado obligatorios."
            )
            return

        options, correct = self.table.collect()
        if len(options) < 3 or correct == 0:
            QMessageBox.warning(
                self,
                "Datos incompletos",
                "Añade ≥3 opciones y marca la(s) correcta(s).",
            )
            return

        with SessionLocal() as s:
            subj_obj = s.query(m.Subject).filter_by(name=subj).first() or m.Subject(
                name=subj
            )

            q = m.MCQQuestion(
                prompt=prompt_txt,
                subject=subj_obj,
                reference=ref or None,
                section=section or None,
            )
            q.options = options
            s.add(q)
            s.commit()

        QMessageBox.information(
            self, "Pregunta guardada", "La pregunta se ha almacenado correctamente."
        )
        super().accept()
