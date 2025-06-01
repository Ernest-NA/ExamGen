"""
examgen/gui/main.py – Ventana principal de ExamGen con selector de tema.

• El tema *Oscuro* se aplica al arrancar.
• Menú “Tema” permite cambiar entre Claro y Oscuro en caliente.
• Menú “Archivo” incluye “Nueva pregunta…”.
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
from PySide6.QtGui import QAction, QActionGroup, QFont
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QStatusBar,
)

from examgen import models as m
from examgen.gui.dialogs import QuestionDialog
from examgen.gui.style import Style


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
        self._update_subject_count()
        self._update_status()

    # --------------------------------------------------------------------- #
    #  Menú                                                                  #
    # --------------------------------------------------------------------- #
    def _create_menu_bar(self) -> None:
        mb = QMenuBar(self)
        self.setMenuBar(mb)

        # --- Archivo ------------------------------------------------------ #
        archivo: QMenu = mb.addMenu("&Archivo")
        archivo.addAction(
            "Nueva &pregunta…",
            self._open_question_dialog,
        )
        archivo.addSeparator()
        archivo.addAction("Salir", QApplication.instance().quit)

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

    def _update_subject_count(self) -> None:
        with m.Session(m.get_engine(DB_PATH)) as s:
            count = s.query(m.Subject).count()
        self.statusBar().showMessage(f"Materias: {count}")

    def _update_status(self) -> None:
        with m.Session(m.get_engine(DB_PATH)) as s:
            subject_count   = s.query(m.Subject).count()
            question_count  = s.query(m.Question).count()
        self.statusBar().showMessage(
            f"Materias: {subject_count}   Preguntas: {question_count}"
    )

    # --------------------------------------------------------------------- #
    #  Temas                                                                #
    # --------------------------------------------------------------------- #
    def _apply_theme(self) -> None:
        QApplication.instance().setStyleSheet(Style.sheet(self.current_theme))

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
            self._update_subject_count()
            self._update_status()


# ------------------------------------------------------------------------- #
#  Entry-point                                                              #
# ------------------------------------------------------------------------- #
def main() -> None:
    m.init_db(DB_PATH)  # crea BD si no existe

    app = QApplication(sys.argv)
    font = QFont()
    font.setPointSize(11)
    app.setFont(font)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
