from __future__ import annotations
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QTextOption, QColor
from PySide6.QtWidgets import QLineEdit
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
)

from examgen import models as m
from examgen.models import SessionLocal

from examgen.services.exam_service import (
    ExamConfig,
    SelectorTypeEnum,
    Attempt,
    evaluate_attempt,
)

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
        painter.drawText(
            option.rect, self._flags, str(index.data(Qt.DisplayRole) or "")
        )
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
        self.verticalHeader().setDefaultSectionSize(
            self.fontMetrics().lineSpacing() + 6
        )
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
            expl = self.item(r, 4).text().strip()[:MAX_CHARS]
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
# ExamConfigDialog
# ------------------------------------------------------------------
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

        # match widths for spin boxes
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

    # ---------------- helpers -----------------
    def _load_subjects(self) -> None:
        """Populate subject combo from the database."""
        with SessionLocal() as s:
            subjects = s.query(m.Subject).order_by(m.Subject.name).all()

        self.cb_subject.clear()
        for subj in subjects:
            self.cb_subject.addItem(subj.name, subj.id)

        if self.cb_subject.isEditable():
            # ensure editable combo before attaching a completer
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

    # ---------------- accept -------------------
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

    # ---------------- convenience -------------
    @classmethod
    def get_config(cls, parent: QWidget | None = None) -> Optional[ExamConfig]:
        dlg = cls(parent)
        return dlg.config if dlg.exec() == cls.Accepted else None


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

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.addWidget(self.cb_subject)
        top.addSpacing(20)
        top.addWidget(QLabel("Referencia:"))
        top.addWidget(self.le_reference)
        w_top = QWidget()
        w_top.setLayout(top)

        # prompt
        self.prompt = QPlainTextEdit()
        self.prompt.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self.counter = QLabel("0/3000", alignment=Qt.AlignRight)
        self.prompt.textChanged.connect(self._update_counter)

        w_prompt = QWidget()
        hp = QHBoxLayout(w_prompt)
        hp.setContentsMargins(0, 0, 0, 0)
        hp.addWidget(self.prompt)

        # table options
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
            QMessageBox.warning(
                self, "Datos incompletos", "Materia y enunciado obligatorios."
            )
            return

        options, correct = self.table.collect()
        if len(options) < 2 or correct == 0:
            QMessageBox.warning(
                self,
                "Datos incompletos",
                "Añade ≥2 opciones y marca la(s) correcta(s).",
            )
            return

        engine = m.get_engine(self.db_path)
        with m.Session(engine) as s:
            subj_obj = s.query(m.Subject).filter_by(name=subj).first() or m.Subject(
                name=subj
            )
            ref_obj = s.query(m.Subject).filter_by(name=ref).first() if ref else None

            q = m.MCQQuestion(
                prompt=prompt_txt,
                subject=subj_obj,
                reference=ref or None,
            )
            q.options = options
            s.add(q)
            s.commit()

        QMessageBox.information(
            self, "Pregunta guardada", "La pregunta se ha almacenado correctamente."
        )
        super().accept()


class ResultsDialog(QDialog):
    """Show exam results with per-question breakdown."""

    def __init__(self, attempt: Attempt, parent: QWidget | None = None) -> None:
        if attempt.ended_at is None:
            attempt = evaluate_attempt(attempt.id)
        super().__init__(parent)
        self.attempt = attempt

        self.setWindowTitle("\u00a1Resultados del examen!")

        title = QLabel("\u00a1Resultados del examen!", alignment=Qt.AlignCenter)
        score = attempt.score or 0
        total = len(attempt.questions)
        pct = round((score / total) * 100) if total else 0
        summary = QLabel(
            f"Puntuaci\u00f3n: {score} / {total}   ({pct} %)",
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
        dlg = cls(attempt, parent)
        dlg.exec()


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    from examgen.models import SessionLocal

    app = QApplication(sys.argv)
    with SessionLocal() as s:
        attempt = s.query(Attempt).order_by(Attempt.id.desc()).first()
    if attempt:
        ResultsDialog.show_for_attempt(attempt)
