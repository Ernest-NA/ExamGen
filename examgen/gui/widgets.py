from __future__ import annotations
from typing import List
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

from examgen.models import Attempt
from examgen.services.exam_service import (
    ExamConfig,
    create_attempt,
    evaluate_attempt,
)

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


class ExamWindow(QWidget):
    """Window showing an ongoing exam attempt with pause and resume."""

    def __init__(self, attempt: Attempt, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.attempt = attempt
        self.remaining_seconds = attempt.time_limit * 60
        self.index = 0

        self.lbl_timer = QLabel(alignment=Qt.AlignLeft)
        self.lbl_progress = QLabel(alignment=Qt.AlignRight)
        self.btn_pause = QPushButton("Pausar", clicked=self._toggle_pause)

        header = QHBoxLayout()
        header.addWidget(self.btn_pause)
        header.addWidget(self.lbl_timer)
        header.addStretch(1)
        header.addWidget(self.lbl_progress)

        self.lbl_prompt = QLabel(wordWrap=True)
        self.group = QButtonGroup(self)
        self.opts: List[QRadioButton] = []
        for _ in range(4):
            rb = QRadioButton()
            self.group.addButton(rb)
            self.opts.append(rb)

        opts_box = QVBoxLayout()
        for rb in self.opts:
            opts_box.addWidget(rb)

        nav = QHBoxLayout()
        self.btn_prev = QPushButton("\u2190 Anterior", clicked=self._prev)
        self.btn_next = QPushButton("Siguiente \u2192", clicked=self._next)
        nav.addWidget(self.btn_prev)
        nav.addStretch(1)
        nav.addWidget(self.btn_next)

        root = QVBoxLayout(self)
        root.addLayout(header)
        root.addWidget(self.lbl_prompt)
        root.addLayout(opts_box)
        root.addLayout(nav)

        QShortcut(QKeySequence("Ctrl+P"), self, activated=self._toggle_pause)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._finish_shortcut)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)

        self._load_question()

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

    def _tick(self) -> None:
        self.remaining_seconds -= 1
        self._update_timer()
        if self.remaining_seconds <= 0:
            self.finish_exam(auto=True)

    def _save_selection(self) -> None:
        selected = self.group.checkedButton()
        text = selected.text() if selected else None
        self.attempt.questions[self.index].selected_option = text

    def _load_question(self) -> None:
        self._update_timer()
        total = len(self.attempt.questions)
        self.lbl_progress.setText(f"Pregunta {self.index + 1} / {total}")

        aq = self.attempt.questions[self.index]
        self.lbl_prompt.setText(aq.question.prompt)

        for rb, opt in zip(self.opts, aq.question.options):
            rb.show()
            rb.setText(opt.text)
            rb.setChecked(aq.selected_option == opt.text)
        for rb in self.opts[len(aq.question.options) :]:
            rb.hide()
            rb.setChecked(False)
            rb.setText("")

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

        msg = "Tiempo finalizado" if auto else "Examen entregado"
        result = f"{msg}.\nPuntuaci\u00f3n: {self.attempt.score}/{len(self.attempt.questions)}"

        def _show() -> None:
            QMessageBox.information(self, "Resultado", result)
            self.close()

        QTimer.singleShot(0, _show)


def start_exam(config: ExamConfig, parent: QWidget | None = None) -> ExamWindow:
    attempt = create_attempt(config)
    win = ExamWindow(attempt, parent)
    win.show()
    return win


if __name__ == "__main__":  # pragma: no cover
    import sys
    from PySide6.QtWidgets import QApplication
    from examgen.gui.dialogs import ExamConfigDialog

    app = QApplication(sys.argv)
    dlg = ExamConfigDialog()
    if dlg.exec() == dlg.Accepted and dlg.config:
        win = start_exam(dlg.config)
        print("Botón Pausar disponible")
        sys.exit(app.exec())
