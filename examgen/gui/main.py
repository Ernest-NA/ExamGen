"""
examgen/gui/main.py – Ventana principal de ExamGen con selector de tema.

• El tema *Oscuro* se aplica al arrancar.
• Menú “Tema” permite cambiar entre Claro y Oscuro en caliente.
• Menú “Archivo” incluye “Preguntas…”.
"""

from __future__ import annotations

import sys
from pathlib import Path
from dotenv import load_dotenv
import logging
import os

env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)

DB_PATH = Path(os.getenv("EXAMGEN_DB", "examgen.db"))  # ruta BD
LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING").upper()
THEME = os.getenv("EXAMGEN_THEME", "Oscuro")

logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.WARNING))
if LOG_LEVEL == "DEBUG":
    print(f"Loaded .env from {env_path}")
    print(f"DB path: {DB_PATH}")
    print(f"Theme  : {THEME}")

try:
    from examgen.config import set_theme  # type: ignore
except Exception:
    set_theme = None
if set_theme:
    set_theme(THEME)

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QFont, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QStatusBar,
    QMessageBox,
    QWidget,
)

from examgen import models as m
from examgen.models import SessionLocal
from examgen.gui.dialogs import QuestionDialog
from examgen.gui.style import Style
from examgen.ui.styles import apply_app_styles, BUTTON_STYLE


class MainWindow(QMainWindow):
    """Ventana principal con cambio de tema en tiempo real."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ExamGen")
        self.resize(1280, 720)

        # Tema actual
        self.current_theme = THEME
        self._apply_theme()

        # Widget central placeholder
        self.setCentralWidget(
            QLabel("ExamGen – bienvenido", alignment=Qt.AlignmentFlag.AlignCenter)
        )

        # Menú y barra de estado
        self._create_menu_bar()
        self._create_status_bar()
        self.lbl_stats = QLabel(self)
        self.statusBar().addWidget(self.lbl_stats)
        self.lbl_stats.setContentsMargins(4, 0, 0, 0)
        self._refresh_stats()

    # --------------------------------------------------------------------- #
    #  Menú                                                                  #
    # --------------------------------------------------------------------- #
    def _create_menu_bar(self) -> None:
        mb = QMenuBar(self)
        self.setMenuBar(mb)

        # --- Archivo ------------------------------------------------------ #
        archivo: QMenu = mb.addMenu("&Archivo")

        window = self

        def _do_exam() -> None:
            from examgen.gui.dialogs import ExamConfigDialog
            from examgen.gui.widgets import start_exam

            cfg = ExamConfigDialog.get_config(window)
            if cfg:
                try:
                    if start_exam(cfg, parent=window):
                        print("Examen completado")
                except ValueError:
                    QMessageBox.warning(
                        window,
                        "No hay preguntas",
                        f'No hay preguntas para la materia "{cfg.subject}"',
                    )

        exam_action = QAction("Hacer examen…", self)
        exam_action.setShortcut(QKeySequence("Ctrl+E"))
        exam_action.triggered.connect(_do_exam)
        archivo.addAction(exam_action)

        act_questions = QAction("Preguntas", self)
        act_questions.triggered.connect(self._show_questions)
        archivo.addAction(act_questions)
        history_action = QAction("Historial", self)
        history_action.triggered.connect(self._show_history)
        archivo.addAction(history_action)
        archivo.addSeparator()
        archivo.addAction("Salir", QApplication.instance().quit)

        # --- Examen ------------------------------------------------------- #
        # Eliminado. Acción "Hacer examen..." movida al menú Archivo.

        # --- Tema --------------------------------------------------------- #
        tema: QMenu = mb.addMenu("&Tema")
        group = QActionGroup(self, exclusive=True)

        for name in ("Claro", "Oscuro"):
            act = QAction(name, self, checkable=True)
            act.setChecked(name == self.current_theme)
            act.triggered.connect(lambda _=False, n=name: self._switch_theme(n))
            group.addAction(act)
            tema.addAction(act)

    # --------------------------------------------------------------------- #
    #  Barra de estado                                                      #
    # --------------------------------------------------------------------- #
    def _create_status_bar(self) -> None:
        sb = QStatusBar(self)
        self.setStatusBar(sb)
        sb = self.statusBar()
        # Oculta el borde que QT dibuja en cada item del status-bar
        sb.setStyleSheet("QStatusBar::item { border: 0px solid transparent; }")

    def _refresh_stats(self) -> None:
        with SessionLocal() as s:
            num_subj = s.query(m.Subject).count()
            num_q = s.query(m.MCQQuestion).count()
        self.lbl_stats.setText(f"Materias: {num_subj}   Preguntas: {num_q}")

    # --------------------------------------------------------------------- #
    #  Temas                                                                #
    # --------------------------------------------------------------------- #
    def _apply_theme(self) -> None:
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(Style.sheet(self.current_theme) + BUTTON_STYLE)

    def _switch_theme(self, target: str) -> None:
        if target != self.current_theme:
            self.current_theme = target
            self._apply_theme()
            # Actualizar checks del menú
            for act in self.menuBar().findChildren(QAction):
                if act.text() in ("Claro", "Oscuro"):
                    act.setChecked(act.text() == self.current_theme)

    # --------------------------------------------------------------------- #
    #  Diálogo de pregunta                                                  #
    # --------------------------------------------------------------------- #
    def _open_question_dialog(self) -> None:
        if QuestionDialog(self, db_path=DB_PATH).exec():
            self._refresh_stats()

    def _show_questions(self) -> None:
        from examgen.gui.questions_window import QuestionsWindow

        win = QuestionsWindow()
        win.show()

    def _show_history(self) -> None:
        from examgen.gui.dialogs import AttemptsHistoryDialog

        AttemptsHistoryDialog(self).exec()


# ------------------------------------------------------------------------- #
#  Entry-point                                                              #
# ------------------------------------------------------------------------- #
def main() -> None:
    m.init_db(DB_PATH)  # crea BD si no existe

    app = QApplication(sys.argv)
    apply_app_styles(app)
    font = QFont()
    font.setPointSize(11)
    app.setFont(font)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
