from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable
import random
import time

from pathlib import Path

from PySide6.QtCore import (
    Qt,
    QTimer,
    Slot,
    QPropertyAnimation,
    QParallelAnimationGroup,
    QAbstractAnimation,
)
from PySide6.QtGui import QKeySequence, QShortcut, QFont, QIcon
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QCheckBox,
    QProgressBar,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QFrame,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from examgen.core.models import Attempt, AttemptQuestion
from examgen.core.database import SessionLocal
from examgen.core.services.exam_service import evaluate_attempt
from examgen.gui.dialogs.results_dialog import ResultsDialog
from examgen.utils.debug import (
    jlog,
    mark_render_start,
    render_elapsed,
)


@dataclass(slots=True)
class OptionWidgetInfo:
    widget: QAbstractButton
    letter: str
    is_correct: bool
    explanation: str
    frame_exp: QFrame
    label_exp: QLabel


class ExamPage(QWidget):
    """Exam view integrated as a page."""

    def __init__(
        self,
        attempt: Attempt,
        on_finished: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setStyleSheet(Path(__file__).with_suffix('.qss').read_text())
        self.attempt = attempt
        self.on_finished = on_finished
        self.remaining_seconds = attempt.time_limit * 60
        self.index = 0
        self._frames_expl: list[QFrame] = []
        self._expl_visible = False
        self.num_correct = 0
        self.current_aq: AttemptQuestion | None = None
        # keep running animations alive to avoid premature GC
        self._fx_animations: list[QAbstractAnimation] = []

        bold = QFont()
        bold.setBold(True)
        self.lbl_subject = QLabel(f"Materia: {attempt.subject}")
        self.lbl_subject.setFont(bold)
        self.lbl_timer = QLabel(alignment=Qt.AlignRight)
        self.lbl_progress = QLabel(alignment=Qt.AlignCenter)
        self.btn_pause = QPushButton("Pausar", clicked=self._toggle_pause)
        self.btn_toggle = QPushButton("Revisar Explicación \u25bc")
        self.btn_toggle.clicked.connect(self._toggle_all_expl)
        self.btn_toggle.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.btn_prev = QPushButton("\u2190 Anterior", clicked=self._prev)
        self.btn_next = QPushButton("Siguiente \u2192", clicked=self._next)

        for b, tip in (
            (self.btn_prev, "Anterior (←)"),
            (self.btn_next, "Siguiente (→ / Enter)"),
            (self.btn_pause, "Pausar/Reanudar (P)"),
            (self.btn_toggle, "Mostrar Explicación (E)"),
        ):
            b.setToolTip(tip)
            b.setAccessibleName(b.text())

        header = QHBoxLayout()
        header.setContentsMargins(0, 12, 0, 4)
        header.setSpacing(8)
        header.addWidget(self.lbl_subject)
        header.addStretch(1)
        header.addWidget(self.lbl_progress)
        header.addStretch(1)
        header.addWidget(self.lbl_timer)

        header2 = QHBoxLayout()
        header2.setContentsMargins(0, 0, 0, 0)
        header2.addWidget(self.btn_pause)
        header2.addStretch(1)
        header2.addWidget(self.btn_toggle)

        self.lbl_prompt = QLabel(alignment=Qt.AlignJustify)
        self.lbl_prompt.setWordWrap(True)
        self.lbl_prompt.setContentsMargins(0, 8, 0, 0)
        f_prompt = QFont()
        f_prompt.setPointSize(15)
        f_prompt.setWeight(QFont.DemiBold)
        self.lbl_prompt.setFont(f_prompt)
        self.lbl_prompt.setMaximumWidth(960)
        self.lbl_prompt.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Minimum,
        )
        self.group = QButtonGroup(self)
        self.options: list[OptionWidgetInfo] = []
        # Guardaremos aquí todos los widgets de opción
        self._opciones: list[QAbstractButton] = []

        opts_container = QWidget()
        self.opts_panel = opts_container
        self.vbox_opts = QVBoxLayout(opts_container)
        self.vbox_opts.setContentsMargins(0, 0, 0, 0)
        self.vbox_opts.setSpacing(2)  # evita saltos perceptibles

        nav = QHBoxLayout()
        nav.setContentsMargins(0, 0, 0, 0)
        nav.setSpacing(0)
        nav.addWidget(self.btn_prev)
        nav.addStretch(1)
        nav.addWidget(self.btn_next)

        container = QWidget()
        container.setMaximumWidth(1400)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(32, 0, 32, 8)
        container_layout.setSpacing(10)
        container_layout.addLayout(header)
        container_layout.addLayout(header2)
        self.progress = QProgressBar(self, textVisible=False)
        self.progress.setMaximum(len(attempt.questions))
        self.progress.setFixedHeight(4)
        self.progress.setStyleSheet(
            "QProgressBar{background:#333;} "
            "QProgressBar::chunk{background:#4caf50;}"
        )
        container_layout.addWidget(self.progress)
        container_layout.addWidget(self.lbl_prompt)
        container_layout.addWidget(opts_container)
        self.box_expl = QFrame(objectName="explanationBox")
        lay_expl = QVBoxLayout(self.box_expl)
        lay_expl.setContentsMargins(0, 0, 0, 0)
        self.lbl_expl = QLabel(objectName="explanationLabel")
        self.lbl_expl.setWordWrap(True)
        lay_expl.addWidget(self.lbl_expl)
        self.box_expl.setMaximumHeight(0)
        self.anim = QPropertyAnimation(self.box_expl, b"maximumHeight", self)
        self.anim.setDuration(250)
        container_layout.addWidget(self.box_expl)
        container_layout.addLayout(nav)

        scroll = QScrollArea(widgetResizable=True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setWidget(container)
        self.scroll = scroll

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

        QShortcut(
            QKeySequence("Ctrl+P"),
            self,
            activated=self._toggle_pause,
        )
        QShortcut(QKeySequence(Qt.Key_Left), self, activated=self._prev)
        QShortcut(QKeySequence(Qt.Key_Right), self, activated=self._next)
        QShortcut(QKeySequence(Qt.Key_Return), self, activated=self._next)
        QShortcut(QKeySequence(Qt.Key_Enter), self, activated=self._next)
        QShortcut(
            QKeySequence("E"),
            self,
            activated=self._toggle_expand_current,
        )
        QShortcut(QKeySequence("P"), self, activated=self._toggle_pause)
        QShortcut(
            QKeySequence("Ctrl+Return"),
            self,
            activated=self._finish_shortcut,
        )

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)

        self._load_question()

    # ------------------------------------------------------------------
    @staticmethod
    def _fmt(secs: int) -> str:
        m, s = divmod(max(secs, 0), 60)
        return f"\N{clock face three oclock} {m:02d}:{s:02d}"

    def _update_timer(self) -> None:
        t = self._fmt(self.remaining_seconds)
        if self.remaining_seconds < 120:
            color = "#e53935"
        elif self.remaining_seconds < 600:
            color = "#ffb300"
        else:
            color = "#ffffff"
        self.lbl_timer.setText(f"<span style='color:{color}'>{t}</span>")

    def _selecciones_actuales(self) -> int:
        """Devuelve cuántas opciones están marcadas ahora mismo."""
        return sum(1 for w in self._opciones if w.isChecked())

    @Slot()
    def _actualizar_estado_botones(self) -> None:
        # Está completo si el número de selecciones coincide con lo que
        # pide la pregunta
        completado = self._selecciones_actuales() == self.num_correct
        # El alumno debe poder pulsar el botón aunque la explicación esté vacía
        self.btn_toggle.setEnabled(completado)
        self.btn_next.setEnabled(completado)

    @Slot()
    def _on_opcion_toggled(self) -> None:
        """Handle option toggled and update related buttons."""
        before = self.btn_toggle.isEnabled()
        # -- 1) enable toggle button ASAP -------------------------------
        if not before:
            sel = sum(w.isChecked() for w in self._opciones)
            if sel == self.num_correct:
                self.btn_toggle.setEnabled(True)

        # -- 2) enforce selection limits and update --------------------
        sender = self.sender()
        if isinstance(sender, QCheckBox):
            if self._selecciones_actuales() > self.num_correct:
                sender.setChecked(False)
                QMessageBox.information(
                    self,
                    "Máximo alcanzado",
                    (
                        f"Solo puedes elegir {self.num_correct} "
                        "opciones en esta pregunta."
                    ),
                )
                return
        self._actualizar_estado_botones()
        jlog(
            "toggle",
            btn=getattr(sender, "text", lambda: "")(),
            checked=getattr(sender, "isChecked", lambda: False)(),
            sel=self._selecciones_actuales(),
            needed=self.num_correct,
            btn_before=before,
            btn_after=self.btn_toggle.isEnabled(),
        )

    def _toggle_choice(self, btn: QAbstractButton, frame: QFrame) -> None:
        """Expand or collapse *frame* based on *btn* state."""
        state = btn.isChecked()
        end = (
            min(frame.layout().sizeHint().height() + 8, 250)
            if state
            else 0
        )
        self._anim_expand(frame, end)
        if state:
            QTimer.singleShot(
                260, lambda: self.scroll.ensureWidgetVisible(frame)
            )
        self._actualizar_estado_botones()

    def _anim_expand(self, widget: QFrame, end: int) -> None:
        anim = QPropertyAnimation(widget, b"maximumHeight", self)
        anim.setDuration(200)
        anim.setStartValue(widget.maximumHeight())
        anim.setEndValue(end)
        widget.setVisible(True)
        anim.start(QPropertyAnimation.DeleteWhenStopped)

    def _toggle_expand_current(self) -> None:
        """Toggle explanation for currently selected options."""
        for info in self.options:
            if info.widget.isChecked():
                self._toggle_choice(info.widget, info.frame_exp)

    def _set_widgets_enabled(self, enabled: bool) -> None:
        for info in self.options:
            w = info.widget
            w.setAttribute(Qt.WA_TransparentForMouseEvents, not enabled)
            w.setFocusPolicy(Qt.StrongFocus if enabled else Qt.NoFocus)
        if enabled:
            self.btn_prev.setEnabled(self.index > 0)
            self._actualizar_estado_botones()
        else:
            self.btn_prev.setEnabled(False)
            self.btn_next.setEnabled(False)
            self.btn_toggle.setEnabled(False)

    def _tick(self) -> None:
        self.remaining_seconds -= 1
        self._update_timer()
        if self.remaining_seconds <= 0:
            self.finish_exam(auto=True)

    def _save_selection(self) -> None:
        aq = self.attempt.questions[self.index]
        if not self.options:
            return
        if isinstance(self.options[0].widget, QRadioButton):
            sel = next(
                (i.letter for i in self.options if i.widget.isChecked()),
                "",
            )
        else:
            sel = "".join(
                sorted(
                    i.letter for i in self.options if i.widget.isChecked()
                )
            )
        aq.selected_option = sel
        with SessionLocal() as s:
            s.merge(aq)
            s.commit()

    # ------------------------ nav & display ----------------------------
    def _load_question(self) -> None:
        self._update_timer()
        # -- reset explanation state when showing a new question ---------
        self._expl_visible = False
        self.btn_toggle.setText("Revisar Explicación \u25bc")
        self.btn_toggle.setEnabled(False)
        for fr in getattr(self, "_frames_expl", []):
            fr.setMaximumHeight(0)
            fr.setVisible(False)

        mark_render_start()
        total = len(self.attempt.questions)
        self.lbl_progress.setText(f"Pregunta {self.index + 1} / {total}")
        self.progress.setValue(self.index + 1)

        aq = self.attempt.questions[self.index]
        self.current_aq = aq
        q = aq.question
        jlog(
            "load_q",
            q_id=q.id,
            q_idx=self.index + 1,
            q_total=total,
            opts=len(q.options),
        )
        self.lbl_prompt.setText(q.prompt)
        self.lbl_prompt.adjustSize()
        has_expl = bool(
            q.explanation and q.explanation.strip()
        )
        self._has_expl = has_expl
        self.btn_toggle.setEnabled(has_expl)
        self.btn_toggle.setToolTip(
            "" if has_expl else "Esta pregunta no tiene explicación guardada"
        )
        self.btn_toggle.setText("Revisar Explicación \u25bc")
        self.btn_toggle.setEnabled(False)
        self.btn_next.setEnabled(False)
        self.lbl_expl.setText(q.explanation or "")

        options: list[tuple[str, str, bool, str]] = [
            (
                letter,
                opt.text,
                opt.is_correct,
                opt.explanation or "",
            )
            for letter, opt in aq.question.options_dict.items()
            if opt.text
        ]
        random.shuffle(options)
        self.num_correct = sum(1 for _, _, ok, _ in options if ok)
        widget_cls = QRadioButton if self.num_correct == 1 else QCheckBox

        for i in reversed(range(self.vbox_opts.count())):
            item = self.vbox_opts.takeAt(i)
            if item.widget():
                item.widget().deleteLater()

        self.options.clear()
        self._opciones.clear()
        self._frames_expl = []
        if self.num_correct == 1:
            self.group = QButtonGroup(self)
            self.group.setExclusive(True)
        for letter, text, is_ok, expl in options:
            w = widget_cls(text, self)
            w.setObjectName("optionButton")
            w.setAccessibleName(f"Opcion {letter}")
            if isinstance(w, QRadioButton):
                self.group.addButton(w)
            frame = QFrame(self, objectName="explFrame")
            frame.setVisible(False)
            frame.setMaximumHeight(0)
            lay = QVBoxLayout(frame)
            lay.setContentsMargins(6, 4, 6, 4)
            lay.setSpacing(4)
            lbl = QLabel(expl, self, objectName="lblExpl")
            lbl.setWordWrap(True)
            lay.addWidget(lbl)

            border = "#4caf50" if is_ok else "#e53935"
            frame.setStyleSheet(
                f"border:1px solid {border};"
                f"background:#141414;"
                f"border-radius:6px;"
                f"color:{border};"
            )
            lbl.setStyleSheet(f"color:{border};")
            info = OptionWidgetInfo(
                widget=w,
                letter=letter,
                is_correct=is_ok,
                explanation=expl,
                frame_exp=frame,
                label_exp=lbl,
            )
            self.options.append(info)
            self._opciones.append(w)
            w.toggled.connect(self._on_opcion_toggled)
            self.vbox_opts.addWidget(w)
            self.vbox_opts.addWidget(frame)
            self._frames_expl.append(frame)
            if isinstance(w, QRadioButton):
                w.setChecked(aq.selected_option == letter)
            else:
                w.setChecked(letter in (aq.selected_option or ""))
        self.btn_prev.setEnabled(self.index > 0)
        if self.index == total - 1:
            self.btn_next.setText("Finalizar")
            self.btn_next.setIcon(QIcon(":/icons/icon_finish.svg"))
            self.btn_next.setToolTip("Finalizar examen (→ / Enter)")
            self.btn_next.setAccessibleName(self.btn_next.text())
        else:
            self.btn_next.setText("Siguiente \u2192")
            self.btn_next.setIcon(QIcon())
            self.btn_next.setToolTip("Siguiente (→ / Enter)")
            self.btn_next.setAccessibleName(self.btn_next.text())

        # Con radios ya recibimos 'toggled' de cada botón; no duplicar.
        if self.options:
            self._on_opcion_toggled()

        jlog(
            "layout",
            scroll=self.scroll.height(),
            opts_panel=self.opts_panel.height(),
            render_ms=render_elapsed(),
        )

    def _toggle_pause(self) -> None:
        if self.timer.isActive():
            self.timer.stop()
            self._set_widgets_enabled(False)
            self.btn_pause.setText("Reanudar")
            self.btn_pause.setStyleSheet("background:#757575; color:white;")
        else:
            if self.remaining_seconds <= 0:
                return
            self.timer.start(1000)
            self._set_widgets_enabled(True)
            self.btn_pause.setText("Pausar")
            self.btn_pause.setStyleSheet("background:#27c64b; color:white;")

    def _finish_shortcut(self) -> None:
        if self.index == len(self.attempt.questions) - 1:
            self._next()

    # util ----------------------------------------------------------------
    def _frame_target_height(self, fr: QFrame) -> int:
        """Return a valid target height for *fr* even when hidden."""
        old_max = fr.maximumHeight()
        fr.setMaximumHeight(16777215)
        fr.layout().activate()
        height = fr.sizeHint().height()
        fr.setMaximumHeight(old_max)
        return min(height + 4, 250)

    def _toggle_all_expl(self) -> None:
        """Show or hide all explanations with a parallel animation."""
        first_time = not self._expl_visible
        self._expl_visible = not self._expl_visible
        if first_time:
            self._save_selection()
            self._evaluate_selection(self.current_aq)
            self._apply_colors(self.current_aq)
            self._freeze_options()

        grp = QParallelAnimationGroup(self)
        h_target = self._frame_target_height

        for fr in self._frames_expl:
            fr.setVisible(True)
            anim = QPropertyAnimation(fr, b"maximumHeight")
            anim.setDuration(220)
            anim.setStartValue(fr.maximumHeight())
            anim.setEndValue(h_target(fr) if self._expl_visible else 0)
            grp.addAnimation(anim)

        self._fx_animations.append(grp)

        start = time.perf_counter()

        def _cleanup() -> None:
            self._fx_animations.remove(grp)
            self.btn_toggle.setEnabled(True)
            anim_ms = int((time.perf_counter() - start) * 1000)
            jlog(
                "show_expl" if self._expl_visible else "hide_expl",
                anim_ms=anim_ms,
                exp_target=[f.sizeHint().height() for f in self._frames_expl],
            )

        grp.finished.connect(_cleanup)

        self.btn_toggle.setEnabled(False)
        self.btn_toggle.setText(
            "Ocultar Explicación \u25b2"
            if self._expl_visible
            else "Revisar Explicación \u25bc"
        )

        grp.start()

        if self._expl_visible:
            QTimer.singleShot(
                240,
                lambda: self.scroll.ensureWidgetVisible(self._frames_expl[0]),
            )

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

    def _freeze_options(self) -> None:
        for info in self.options:
            info.widget.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            info.widget.setFocusPolicy(Qt.NoFocus)

    def _evaluate_selection(self, aq: AttemptQuestion) -> None:
        correct_set = {
            letter
            for letter, opt in zip("ABCDE", aq.question.options)
            if opt.is_correct
        }
        if isinstance(self.options[0].widget, QRadioButton):
            aq.is_correct = aq.selected_option in correct_set
        else:
            aq.is_correct = set(aq.selected_option or "") == correct_set
        with SessionLocal() as s:
            s.merge(aq)
            s.commit()

    def _apply_colors(self, aq: AttemptQuestion) -> None:
        sel_set = set(aq.selected_option or "")
        for info in self.options:
            color = None
            if info.is_correct:
                color = "#5af16a"  # verde
            elif info.letter in sel_set:
                color = "#ff6b6b"  # rojo
            if color:
                info.widget.setStyleSheet(
                    f"color: {color}; padding-left:6px;"
                )
            else:
                info.widget.setStyleSheet("padding-left:6px;")
            info.widget.setText(info.widget.text())
            info.widget.adjustSize()
            info.widget.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            info.widget.setFocusPolicy(Qt.NoFocus)

    # ------------------------ finish ----------------------
    def finish_exam(self, auto: bool) -> None:
        if self.attempt.ended_at is not None:
            return
        if self.timer.isActive():
            self.timer.stop()
        self._save_selection()
        self.attempt.ended_at = datetime.utcnow()
        with SessionLocal() as s:
            s.merge(self.attempt)
            s.commit()

        self.attempt = evaluate_attempt(self.attempt.id)

        def _show() -> None:
            ResultsDialog.show_for_attempt(self.attempt, self)
            if self.on_finished:
                self.on_finished()

        QTimer.singleShot(0, _show)
