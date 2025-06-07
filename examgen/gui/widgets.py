from __future__ import annotations
from typing import List
from datetime import datetime
import random

from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QKeySequence, QShortcut, QIcon
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QCheckBox,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QHeaderView,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QWidget,
    QSizePolicy,
    QAbstractButton,
)

from examgen.models import Attempt, AttemptQuestion, SessionLocal
from examgen.services.exam_service import (
    ExamConfig,
    create_attempt,
    evaluate_attempt,
)
from examgen.gui.dialogs import ResultsDialog

from examgen import models as m

MAX_CHARS = 3000
MIN_ROWS = 4


def clear_layout(layout: QVBoxLayout | QHBoxLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if widget := item.widget():
            widget.deleteLater()


class WrapAnywhereDelegate(QStyledItemDelegate):
    """Delegate that wraps text even without spaces."""

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


class OptionTable(QTableWidget):
    HEADER = ["", "Opción", "Correcta", "Respuesta", "Explicación", ""]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(MIN_ROWS, 6, parent)

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
    def _init_row(self, row: int) -> None:
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
        trash.setFixedSize(QSize(30, 30))
        self.setCellWidget(row, 5, trash)

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

    def _auto_height(self, row: int, _col: int) -> None:
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
        self.num_correct = 0
        self.current_aq: AttemptQuestion | None = None

        self.lbl_subject = QLabel(f"Materia: {attempt.subject}")
        self.lbl_timer = QLabel(alignment=Qt.AlignRight)
        self.lbl_progress = QLabel(alignment=Qt.AlignCenter)
        self.btn_pause = QPushButton("Pausar", clicked=self._toggle_pause)
        self.btn_toggle = QPushButton("Revisar Explicación \u25bc")
        self.btn_toggle.clicked.connect(self.on_toggle_clicked)

        header_grid = QGridLayout()
        header_grid.setColumnStretch(1, 1)
        header_grid.setHorizontalSpacing(12)
        header_grid.setVerticalSpacing(4)
        header_grid.setContentsMargins(0, 0, 0, 0)

        header_grid.addWidget(self.lbl_subject, 0, 0, Qt.AlignLeft)
        header_grid.addWidget(self.lbl_progress, 0, 1, Qt.AlignCenter)
        header_grid.addWidget(self.lbl_timer, 0, 2, Qt.AlignRight)

        header_grid.addWidget(self.btn_pause, 1, 0, Qt.AlignLeft)
        header_grid.addWidget(self.btn_toggle, 1, 2, Qt.AlignRight)

        self.lbl_prompt = QLabel(alignment=Qt.AlignJustify)
        self.lbl_prompt.setWordWrap(True)
        self.lbl_prompt.setContentsMargins(0, 12, 0, 24)
        self.lbl_prompt.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.group = QButtonGroup(self)
        self.opts: List[QRadioButton] = []

        opts_container = QWidget()
        self.vbox_opts = QVBoxLayout(opts_container)
        self.vbox_opts.setContentsMargins(0, 0, 0, 0)


        nav = QHBoxLayout()
        self.btn_prev = QPushButton("\u2190 Anterior", clicked=self._prev)
        self.btn_next = QPushButton("Siguiente \u2192", clicked=self._next)
        nav.addWidget(self.btn_prev)
        nav.addStretch(1)
        nav.addWidget(self.btn_next)

        root = QVBoxLayout(self)
        root.addLayout(header_grid)
        root.addWidget(self.lbl_prompt)
        root.addWidget(opts_container)
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

    def _update_check_state(self, changed_box: QCheckBox) -> None:
        sel_boxes = [b for b in self.opts if isinstance(b, QCheckBox) and b.isChecked()]
        if len(sel_boxes) > self.num_correct:
            changed_box.setChecked(False)
            QMessageBox.information(
                self,
                "Máximo alcanzado",
                f"Solo puedes elegir {self.num_correct} opciones en esta pregunta.",
            )
            sel_boxes.pop()
        ready = len(sel_boxes) == self.num_correct
        self.btn_toggle.setEnabled(ready)
        self.btn_next.setEnabled(ready)

    def _set_widgets_enabled(self, enabled: bool) -> None:
        for rb in self.opts:
            rb.setAttribute(Qt.WA_TransparentForMouseEvents, not enabled)
            rb.setFocusPolicy(Qt.StrongFocus if enabled else Qt.NoFocus)
        if enabled:
            self.btn_prev.setEnabled(self.index > 0)
            if isinstance(self.opts[0], QRadioButton):
                self.btn_next.setEnabled(True)
                self.btn_toggle.setEnabled(self._has_expl)
            else:
                self._update_check_state(self.opts[0])
        else:
            self.btn_prev.setEnabled(False)
            self.btn_next.setEnabled(False)
            self.btn_toggle.setEnabled(False)

    def _lock_widget(self, w: QAbstractButton) -> None:
        """Prevent *w* from receiving mouse or focus events."""
        w.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        w.setFocusPolicy(Qt.NoFocus)

    def _tick(self) -> None:
        self.remaining_seconds -= 1
        self._update_timer()
        if self.remaining_seconds <= 0:
            self.finish_exam(auto=True)

    def _save_selection(self) -> None:
        aq = self.attempt.questions[self.index]
        if not self.opts:
            return
        if isinstance(self.opts[0], QRadioButton):
            sel = next((w.letter for w in self.opts if w.isChecked()), "")
        else:
            sel = "".join(sorted(w.letter for w in self.opts if w.isChecked()))
        aq.selected_option = sel
        with SessionLocal() as s:
            s.merge(aq)
            s.commit()

    # ----- correction helpers -----
    def _freeze_options(self) -> None:
        for w in self.opts:
            self._lock_widget(w)

    def _evaluate_selection(self, aq: AttemptQuestion) -> None:
        correct_set = {
            l for l, opt in zip("ABCDE", aq.question.options) if opt.is_correct
        }
        if isinstance(self.opts[0], QRadioButton):
            aq.is_correct = aq.selected_option in correct_set
        else:
            aq.is_correct = set(aq.selected_option or "") == correct_set
        with SessionLocal() as s:
            s.merge(aq)
            s.commit()

    def _apply_colors(self, aq: AttemptQuestion) -> None:
        """Color options using rich text and lock them."""
        sel_set = set(aq.selected_option or "")

        for w in self.opts:
            color = None
            if w.is_correct:
                color = "#5af16a"  # verde
            elif w.letter in sel_set:
                color = "#ff6b6b"  # rojo

            if color:
                w.setStyleSheet(f"color: {color};")
            else:
                w.setStyleSheet("")
            w.setText(w.raw_text)
            w.adjustSize()

            w.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            w.setFocusPolicy(Qt.NoFocus)

    def _load_question(self) -> None:
        self._update_timer()
        total = len(self.attempt.questions)
        self.lbl_progress.setText(f"Pregunta {self.index + 1} / {total}")

        aq = self.attempt.questions[self.index]
        self.current_aq = aq
        self.expl_shown = False
        self.lbl_prompt.setText(aq.question.prompt)
        self.lbl_prompt.adjustSize()
        has_expl = bool(aq.question.explanation and aq.question.explanation.strip())
        self._has_expl = has_expl
        self.btn_toggle.setEnabled(has_expl)
        self.btn_toggle.setToolTip(
            "" if has_expl else "Esta pregunta no tiene explicación guardada"
        )
        self.btn_toggle.setText("Revisar Explicación \u25bc")
        self.btn_toggle.setEnabled(False)
        self.btn_next.setEnabled(False)

        opts = [
            (l, opt.text, opt.is_correct)
            for l, opt in zip("ABCDE", aq.question.options)
            if opt.text
        ]
        random.shuffle(opts)
        self.num_correct = sum(1 for _, _, ok in opts if ok)
        widget_cls = QRadioButton if self.num_correct == 1 else QCheckBox
        self._opts_data = opts
        clear_layout(self.vbox_opts)
        self.opts = []
        if widget_cls is QRadioButton:
            self.group = QButtonGroup(self)
        for letter, text, is_ok in opts:
            w = widget_cls(text, self)
            w.raw_text = text
            w.letter = letter
            w.is_correct = is_ok
            if isinstance(w, QRadioButton):
                self.group.addButton(w)
            self.opts.append(w)
            exp_text = aq.question.options_dict[letter].explanation or ""
            lbl_exp = QLabel(exp_text, self)
            lbl_exp.setWordWrap(True)
            lbl_exp.setObjectName("OptExplanation")
            lbl_exp.setVisible(False)
            w.lbl_exp = lbl_exp  # type: ignore[attr-defined]

            self.vbox_opts.addWidget(w)
            self.vbox_opts.addWidget(lbl_exp)
            if isinstance(w, QRadioButton):
                w.setChecked(aq.selected_option == letter)
            else:
                w.setChecked(letter in (aq.selected_option or ""))
                w.stateChanged.connect(lambda _, b=w: self._update_check_state(b))
        self.btn_prev.setEnabled(self.index > 0)
        if self.index == total - 1:
            self.btn_next.setText("Finalizar")
        else:
            self.btn_next.setText("Siguiente \u2192")

        if widget_cls is QRadioButton:
            self.btn_toggle.setEnabled(has_expl)
            self.btn_next.setEnabled(True)
        else:
            self._update_check_state(self.opts[0])

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


    def on_toggle_clicked(self) -> None:
        if not self.expl_shown:
            self._save_selection()
            self._evaluate_selection(self.current_aq)
            self._apply_colors(self.current_aq)
            self._freeze_options()
            for w in self.opts:
                w.lbl_exp.setVisible(bool(w.lbl_exp.text().strip()))
            self.expl_shown = True
            self.btn_toggle.setText("Ocultar Explicaci\u00f3n \u25b2")
        else:
            for w in self.opts:
                w.lbl_exp.setVisible(False)
            self.expl_shown = False
            self.btn_toggle.setText("Revisar Explicaci\u00f3n \u25bc")

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
