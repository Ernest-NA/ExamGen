from __future__ import annotations
from typing import List
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QLabel,
    QFrame,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QSizePolicy,
)

from examgen.models import Attempt, AttemptQuestion, SessionLocal
from examgen.services.exam_service import (
    ExamConfig,
    create_attempt,
    evaluate_attempt,
)
from examgen.gui.dialogs import ResultsDialog

from examgen import models as m


class OptionTable(QTableWidget):
    """Table with text column and a checkable 'Correcta' column."""

    def __init__(self, rows: int = 4, parent: QDialog | None = None):
        super().__init__(rows, 2, parent)
        self.setHorizontalHeaderLabels(["Opción", "Correcta"])
        self.horizontalHeader().setStretchLastSection(True)
        self.setColumnWidth(0, 340)
        self.setColumnWidth(1, 90)
        self._populate_checkboxes()

    def _populate_checkboxes(self) -> None:
        for row in range(self.rowCount()):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Unchecked)
            self.setItem(row, 1, chk)

    def collect_options(self) -> tuple[List[m.AnswerOption], int]:
        """Return list of AnswerOption and number of correct answers."""
        opts: List[m.AnswerOption] = []
        correct = 0
        for r in range(self.rowCount()):
            txt_item = self.item(r, 0)
            if not txt_item or not txt_item.text().strip():
                continue
            chk_item = self.item(r, 1)
            is_corr = (
                chk_item.checkState() == Qt.CheckState.Checked if chk_item else False
            )
            if is_corr:
                correct += 1
            opts.append(
                m.AnswerOption(text=txt_item.text().strip(), is_correct=is_corr)
            )
        return opts, correct


MAX_RATIO = 0.40


class ExamDialog(QDialog):
    """Modal dialog showing an ongoing exam attempt with pause and resume."""

    def __init__(self, attempt: Attempt, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowModality(Qt.ApplicationModal)
        self.attempt = attempt
        self.remaining_seconds = attempt.time_limit * 60
        self.index = 0
        self._has_expl = False
        self.expl_shown = False
        self.current_aq: AttemptQuestion | None = None

        self.lbl_subject = QLabel(f"Materia: {attempt.subject}")
        self.lbl_timer = QLabel(alignment=Qt.AlignRight)
        self.lbl_progress = QLabel(alignment=Qt.AlignCenter)
        self.btn_pause = QPushButton("Pausar", clicked=self._toggle_pause)
        self.btn_toggle = QPushButton(
            "Revisar Explicación \u25bc", clicked=self.on_toggle_clicked
        )

        header = QHBoxLayout()
        header.addWidget(self.lbl_subject)
        header.addStretch(1)
        header.addWidget(self.lbl_progress)
        header.addWidget(self.lbl_timer)

        btn_bar = QHBoxLayout()
        btn_bar.addWidget(self.btn_pause)
        btn_bar.addStretch(1)
        btn_bar.addWidget(self.btn_toggle)

        self.lbl_prompt = QLabel(alignment=Qt.AlignJustify)
        self.lbl_prompt.setWordWrap(True)
        self.lbl_prompt.setContentsMargins(0, 12, 0, 24)
        self.lbl_prompt.setSizePolicy(
            QSizePolicy.Preferred, QSizePolicy.MinimumExpanding
        )
        self.group = QButtonGroup(self)
        self.opts: List[QRadioButton] = []
        for _ in range(4):
            rb = QRadioButton()
            self.group.addButton(rb)
            self.opts.append(rb)

        opts_container = QWidget()
        opts_box = QVBoxLayout(opts_container)
        opts_box.setContentsMargins(0, 0, 0, 0)
        for rb in self.opts:
            opts_box.addWidget(rb)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)

        self.lbl_expl = QLabel(wordWrap=True, alignment=Qt.AlignJustify)
        self.scroll_expl = QScrollArea(widgetResizable=True)
        self.frm_expl = QFrame(self)
        self.frm_expl.setObjectName("ExplanationPanel")
        self.frm_expl.setFrameShape(QFrame.NoFrame)
        self.frm_expl.setStyleSheet(
            "QFrame#ExplanationPanel {"
            " background-color: rgba(255,255,255,0.03);"
            " border-top: 1px solid rgba(255,255,255,0.12);"
            "}"
            "QScrollArea { border: none; }"
        )
        self.scroll_expl.setWidget(self.lbl_expl)
        self.scroll_expl.setFrameStyle(QFrame.NoFrame)
        self.lbl_expl.setContentsMargins(12, 8, 12, 8)
        expl_layout = QVBoxLayout(self.frm_expl)
        expl_layout.setContentsMargins(0, 0, 0, 0)
        expl_layout.addWidget(self.scroll_expl)
        self.scroll_expl.setMaximumHeight(0)
        self.scroll_expl.setVisible(False)

        nav = QHBoxLayout()
        self.btn_prev = QPushButton("\u2190 Anterior", clicked=self._prev)
        self.btn_next = QPushButton("Siguiente \u2192", clicked=self._next)
        nav.addWidget(self.btn_prev)
        nav.addStretch(1)
        nav.addWidget(self.btn_next)

        root = QVBoxLayout(self)
        root.addLayout(header)
        root.addLayout(btn_bar)
        root.addWidget(self.lbl_prompt)
        root.addWidget(opts_container)
        root.addWidget(line)
        root.addWidget(self.frm_expl)
        root.addLayout(nav)

        QShortcut(QKeySequence("Ctrl+P"), self, activated=self._toggle_pause)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._finish_shortcut)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)

        self._load_question()

        if parent:
            self.resize(parent.size())
            self.move(parent.pos())
        else:
            self.resize(1024, 768)
        self.lbl_prompt.setMaximumWidth(int(self.width() * 0.70))

    # ------------------------ helpers ---------------------
    @staticmethod
    def _fmt(secs: int) -> str:
        m, s = divmod(max(secs, 0), 60)
        return f"Tiempo: {m:02d}:{s:02d}"

    def _update_timer(self) -> None:
        self.lbl_timer.setText(self._fmt(self.remaining_seconds))

    def _set_widgets_enabled(self, enabled: bool) -> None:
        for rb in self.opts:
            rb.setEnabled(enabled)
        if enabled:
            self.btn_prev.setEnabled(self.index > 0)
            self.btn_next.setEnabled(True)
        else:
            self.btn_prev.setEnabled(False)
            self.btn_next.setEnabled(False)
        self.btn_toggle.setEnabled(enabled and getattr(self, "_has_expl", False))

    def _tick(self) -> None:
        self.remaining_seconds -= 1
        self._update_timer()
        if self.remaining_seconds <= 0:
            self.finish_exam(auto=True)

    def _save_selection(self) -> None:
        selected = self.group.checkedButton()
        text = selected.text() if selected else None
        self.attempt.questions[self.index].selected_option = text

    # ----- correction helpers -----
    def _freeze_options(self) -> None:
        for rb in self.opts:
            rb.setEnabled(False)

    def _evaluate_selection(self, aq: AttemptQuestion) -> None:
        sel = aq.selected_option
        correct = next(
            (opt.text for opt in aq.question.options if opt.is_correct), None
        )
        aq.is_correct = sel == correct
        with SessionLocal() as s:
            s.merge(aq)
            s.commit()

    def _apply_colors(self, aq: AttemptQuestion) -> None:
        correct = next(
            (letter for letter, opt in zip("ABCD", aq.question.options) if opt.is_correct),
            "",
        )
        selected = next(
            (letter for letter, opt in zip("ABCD", aq.question.options) if opt.text == aq.selected_option),
            "",
        )
        for rb, letter in zip(self.opts, "ABCD"):
            if letter == correct:
                rb.setStyleSheet("color: lightgreen;")
            elif letter == selected:
                rb.setStyleSheet("color: salmon;")

    def _load_question(self) -> None:
        self._update_timer()
        total = len(self.attempt.questions)
        self.lbl_progress.setText(f"Pregunta {self.index + 1} / {total}")

        aq = self.attempt.questions[self.index]
        self.current_aq = aq
        self.expl_shown = False
        self.lbl_prompt.setText(aq.question.prompt)
        expl = aq.question.explanation or "Sin explicación disponible."
        self.lbl_expl.setText(expl)
        has_expl = bool(aq.question.explanation and aq.question.explanation.strip())
        self._has_expl = has_expl
        self.btn_toggle.setEnabled(has_expl)
        self.btn_toggle.setToolTip(
            "" if has_expl else "Esta pregunta no tiene explicación guardada"
        )
        self.scroll_expl.setMaximumHeight(0)
        self.scroll_expl.setVisible(False)
        self.btn_toggle.setText("Revisar Explicación \u25bc")

        for rb, opt in zip(self.opts, aq.question.options):
            rb.show()
            rb.setText(opt.text)
            rb.setChecked(aq.selected_option == opt.text)
            rb.setEnabled(True)
            rb.setStyleSheet("color: black;")
        for rb in self.opts[len(aq.question.options) :]:
            rb.hide()
            rb.setChecked(False)
            rb.setText("")

        if aq.is_correct is not None:
            self._freeze_options()
            self._apply_colors(aq)

        self.btn_prev.setEnabled(self.index > 0)
        if self.index == total - 1:
            self.btn_next.setText("Finalizar")
        else:
            self.btn_next.setText("Siguiente \u2192")

    def _toggle_pause(self) -> None:
        if self.timer.isActive():
            self.timer.stop()
            self._set_widgets_enabled(False)
            self.btn_pause.setText("Reanudar")
        else:
            if self.remaining_seconds <= 0:
                return
            self.timer.start(1000)
            self._set_widgets_enabled(True)
            self.btn_pause.setText("Pausar")

    def _finish_shortcut(self) -> None:
        if self.index == len(self.attempt.questions) - 1:
            self._next()

    def toggle_explanation(self, expand: bool | None = None) -> None:
        expanded = self.scroll_expl.maximumHeight() > 0
        expand = (not expanded) if expand is None else expand
        target = int(self.height() * MAX_RATIO) if expand else 0
        if target > 0:
            self.scroll_expl.setVisible(True)

        anim = QPropertyAnimation(self.scroll_expl, b"maximumHeight", self)
        anim.setDuration(200)
        anim.setStartValue(self.scroll_expl.maximumHeight())
        anim.setEndValue(target)

        def on_finished() -> None:
            self.scroll_expl.setVisible(target > 0)

        anim.finished.connect(on_finished)
        anim.start(QPropertyAnimation.DeleteWhenStopped)

    def on_toggle_clicked(self) -> None:
        if not self.expl_shown:
            self._freeze_options()
            self._evaluate_selection(self.current_aq)
            self._apply_colors(self.current_aq)
            self.expl_shown = True
            self.btn_toggle.setText("Ocultar Explicación \u25b2")
            self.toggle_explanation(expand=True)
        else:
            self.expl_shown = False
            self.btn_toggle.setText("Revisar Explicación \u25bc")
            self.toggle_explanation(expand=False)

    # ------------------------ nav -------------------------
    def _prev(self) -> None:
        if self.index == 0:
            return
        self._save_selection()
        self.index -= 1
        self._load_question()

    def _next(self) -> None:
        self._save_selection()
        if self.index < len(self.attempt.questions) - 1:
            self.index += 1
            self._load_question()
        else:
            reply = QMessageBox.question(
                self,
                "Entregar examen",
                "¿Seguro que deseas entregar el examen?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self.finish_exam(auto=False)

    # ------------------------ finish ----------------------
    def finish_exam(self, auto: bool) -> None:
        if self.attempt.ended_at is not None:
            return
        if self.timer.isActive():
            self.timer.stop()
        self._save_selection()
        self.attempt.ended_at = datetime.utcnow()
        self.attempt = evaluate_attempt(self.attempt.id)

        def _show() -> None:
            ResultsDialog.show_for_attempt(self.attempt, self)
            self.accept()

        QTimer.singleShot(0, _show)


def start_exam(config: ExamConfig, parent: QWidget | None = None) -> bool:
    """Launch a modal exam dialog and return True if completed."""
    attempt = create_attempt(config)
    dlg = ExamDialog(attempt, parent)
    return dlg.exec() == QDialog.Accepted


if __name__ == "__main__":  # pragma: no cover
    import sys
    from PySide6.QtWidgets import QApplication
    from examgen.gui.dialogs import ExamConfigDialog

    app = QApplication(sys.argv)
    dlg = ExamConfigDialog()
    if dlg.exec() == dlg.Accepted and dlg.config:
        start_exam(dlg.config)
        print("Botón Pausar disponible")
        sys.exit(app.exec())
