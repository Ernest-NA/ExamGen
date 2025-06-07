from __future__ import annotations
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QSize, QFile, QIODevice
from PySide6.QtGui import QIcon, QTextOption, QColor
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QLineEdit
from PySide6.QtWidgets import (
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
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QCompleter,
)

from examgen.gui.widgets import OptionTable

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
# ExamConfigDialog
# ------------------------------------------------------------------
class ExamConfigDialog(QDialog):
    """Dialog to configure exam parameters."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.config: Optional[ExamConfig] = None

        ui_file = QFile("examgen/gui/ui/ExamConfigDialog.ui")
        ui_file.open(QIODevice.ReadOnly)
        QUiLoader().load(ui_file, self)
        ui_file.close()

        # widgets from .ui
        self.buttons: QDialogButtonBox = self.findChild(QDialogButtonBox, "buttons")
        self.btn_ok: QPushButton = self.buttons.button(QDialogButtonBox.Ok)
        self.cb_subject: QComboBox = self.findChild(QComboBox, "cb_subject")
        self.spin_time: QSpinBox = self.findChild(QSpinBox, "spin_time")
        self.spin_questions: QSpinBox = self.findChild(QSpinBox, "spin_questions")
        self.rb_random: QRadioButton = self.findChild(QRadioButton, "rb_random")
        self.rb_errors: QRadioButton = self.findChild(QRadioButton, "rb_errors")
        self.lbl_no_subjects: QLabel = self.findChild(QLabel, "lbl_no_subjects")

        self.group = QButtonGroup(self)
        self.group.addButton(self.rb_random)
        self.group.addButton(self.rb_errors)

        self.buttons.rejected.connect(self.reject)

        self.btn_ok.clicked.connect(self._accept)
        self.cb_subject.currentTextChanged.connect(self._update_ok_state)
        self.group.buttonClicked.connect(self._update_ok_state)
        self.spin_questions.valueChanged.connect(self._update_ok_state)
        self.spin_time.valueChanged.connect(self._update_ok_state)

        self._load_subjects()
        self._update_selector()

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

    def _accept(self) -> None:
        self.accept()

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
        ui_file = QFile("examgen/gui/ui/QuestionDialog.ui")
        ui_file.open(QIODevice.ReadOnly)
        QUiLoader().load(ui_file, self)
        ui_file.close()

        self.buttons: QDialogButtonBox = self.findChild(QDialogButtonBox, "buttons")
        self.btn_ok: QPushButton = self.buttons.button(QDialogButtonBox.Save)
        self.cb_subject: QComboBox = self.findChild(QComboBox, "cb_subject")
        self.le_reference: QLineEdit = self.findChild(QLineEdit, "le_reference")
        self.prompt: QPlainTextEdit = self.findChild(QPlainTextEdit, "prompt")
        self.counter: QLabel = self.findChild(QLabel, "counter")
        self.table: OptionTable = self.findChild(OptionTable, "table")
        self.btn_add: QPushButton = self.findChild(QPushButton, "btn_add")

        self.buttons.rejected.connect(self.reject)
        self.btn_ok.clicked.connect(self.accept)
        self.prompt.textChanged.connect(self._update_counter)
        if self.btn_add is not None:
            self.btn_add.clicked.connect(self.table.add_row)

        self._load_subjects()
        self._update_counter()

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

        table = QTableWidget(len(attempt.questions), 4, self)
        table.setHorizontalHeaderLabels(["#", "Pregunta", "Tu resp.", "Correcta"])
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)

        for row, aq in enumerate(attempt.questions, start=0):
            qitem = QTableWidgetItem(str(row + 1))
            qitem.setFlags(Qt.ItemIsEnabled)
            qitem.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 0, qitem)

            prompt = aq.question.prompt[:60]
            pitem = QTableWidgetItem(prompt)
            pitem.setFlags(Qt.ItemIsEnabled)
            table.setItem(row, 1, pitem)

            sel_text = aq.selected_option or ""
            sitem = QTableWidgetItem(sel_text)
            sitem.setFlags(Qt.ItemIsEnabled)
            table.setItem(row, 2, sitem)

            corr_text = next((o.text for o in aq.question.options if o.is_correct), "")
            citem = QTableWidgetItem(corr_text)
            citem.setFlags(Qt.ItemIsEnabled)
            table.setItem(row, 3, citem)

            color = QColor("lightgreen") if aq.is_correct else QColor("salmon")
            for c in range(4):
                table.item(row, c).setBackground(color)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, parent=self)
        buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addWidget(title)
        root.addWidget(summary)
        root.addWidget(table)
        root.addWidget(buttons, alignment=Qt.AlignCenter)

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
