"""Ventana principal de ExamGen.

Carga el tema guardado en ``settings.json`` y ofrece menús:
* **Configuración** – Tema… y Salir.
* **Aplicación** – Hacer examen…, Preguntas e Historial.
"""

from __future__ import annotations

import sys
from pathlib import Path
from dotenv import load_dotenv
import logging
import os

env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(env_path)

from examgen.core.settings import AppSettings

settings = AppSettings.load()
DB_HOME = Path.home() / "Documents" / "examgen.db"
DB_PATH = Path(settings.data_db_path or DB_HOME)
LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING").upper()
THEME_MAP = {"dark": "Oscuro", "light": "Claro"}
THEME = THEME_MAP.get(settings.theme, "Oscuro")

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

from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMenuBar,
    QStatusBar,
    QMessageBox,
    QWidget,
    QStackedWidget,
)

from examgen.core import models as m
from examgen.gui.dialogs.question_dialog import QuestionDialog
from examgen.gui.style import Style
from examgen.ui.styles import apply_app_styles, BUTTON_STYLE


class MainWindow(QMainWindow):
    """Ventana principal con cambio de tema en tiempo real."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ExamGen")
        self.resize(1280, 720)

        # Settings y tema actual
        self.settings = settings
        self.current_theme = THEME
        self._apply_theme()

        # --- stack central ---
        self.pages = QStackedWidget()
        self.setCentralWidget(self.pages)
        self._page_lookup: dict[str, QWidget] = {}

        # -- las páginas se eligen desde el menú principal --

        # página inicial
        self._show_page("questions")

        # Menú y barra de estado
        self._create_menu_bar()
        self._create_status_bar()
        self._set_app_actions_enabled(bool(self.settings.data_db_path))

    # --------------------------------------------------------------------- #
    #  Menú                                                                  #
    # --------------------------------------------------------------------- #
    def _create_menu_bar(self) -> None:
        mb = QMenuBar(self)
        self.setMenuBar(mb)

        # --- Archivo ------------------------------------------------------ #
        menu_file = mb.addMenu("Archivo")

        act_settings = QAction("Configuración…", self)
        act_settings.triggered.connect(lambda: self._show_page("settings"))
        act_exit = QAction("Salir", self, triggered=self.close)

        menu_file.addAction(act_settings)
        menu_file.addSeparator()
        menu_file.addAction(act_exit)

        # --- Aplicación --------------------------------------------------- #
        self.menu_app = mb.addMenu("Aplicación")

        self.act_exam = QAction("Hacer examen…", self)
        self.act_exam.triggered.connect(self._start_exam)
        self.act_questions = QAction("Preguntas", self)
        self.act_questions.triggered.connect(
            lambda: self._show_page("questions")
        )
        self.act_history = QAction("Historial", self)
        self.act_history.triggered.connect(
            lambda: self._show_page("history")
        )

        self.menu_app.addActions(
            [self.act_exam, self.act_questions, self.act_history]
        )

        self.menu_app.aboutToShow.connect(self._warn_if_disabled)

        self._menu_actions = {
            "config": act_settings,
            "exam": self.act_exam,
            "questions": self.act_questions,
            "history": self.act_history,
        }

    def _start_exam(self) -> None:
        from examgen.gui.dialogs.question_dialog import ExamConfigDialog
        from examgen.gui.widgets.option_table import start_exam

        cfg = ExamConfigDialog.get_config(self)
        if cfg:
            try:
                if start_exam(cfg, parent=self):
                    print("Examen completado")
            except ValueError:
                QMessageBox.warning(
                    self,
                    "No hay preguntas",
                    f'No hay preguntas para la materia "{cfg.subject}"',
                )

    def _open_settings(self) -> None:
        self._show_page("settings")

    def _set_app_actions_enabled(self, enabled: bool) -> None:
        for act in (self.act_exam, self.act_questions, self.act_history):
            act.setEnabled(enabled)

    def _warn_if_disabled(self) -> None:
        if not self.act_exam.isEnabled():
            QMessageBox.warning(
                self,
                "Base de datos no seleccionada",
                (
                    "Primero selecciona una base de datos en "
                    "Archivo \u25ba Configuración."
                ),
            )
            self.menu_app.hideTearOffMenu()

    # --------------------------------------------------------------------- #
    #  Barra de estado                                                      #
    # --------------------------------------------------------------------- #
    def _create_status_bar(self) -> None:
        sb = QStatusBar(self)
        self.setStatusBar(sb)
        sb = self.statusBar()
        # Oculta el borde que QT dibuja en cada item del status-bar
        sb.setStyleSheet("QStatusBar::item { border: 0px solid transparent; }")

    # --------------------------------------------------------------------- #
    #  Temas                                                                #
    # --------------------------------------------------------------------- #
    def _apply_theme(self) -> None:
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(Style.sheet(self.current_theme) + BUTTON_STYLE)

    # ------------------------------------------------------------------ #
    #  Navegación                                                        #
    # ------------------------------------------------------------------ #
    def _show_page(self, name: str) -> None:
        if name not in self._page_lookup:
            if name == "questions":
                from examgen.gui.pages.questions_page import QuestionsPage

                widget = QuestionsPage(self)
            elif name == "history":
                from examgen.gui.pages.history_page import HistoryPage

                widget = HistoryPage(self)
            elif name == "settings":
                from examgen.gui.pages.settings_page import SettingsPage

                widget = SettingsPage(self.settings, self)
            else:
                return
            self._page_lookup[name] = widget
            self.pages.addWidget(widget)
        if self.pages.currentWidget() is not self._page_lookup[name]:
            self.pages.setCurrentWidget(self._page_lookup[name])

    # --------------------------------------------------------------------- #
    #  Diálogo de pregunta                                                  #
    # --------------------------------------------------------------------- #
    def _open_question_dialog(self) -> None:
        QuestionDialog(self, db_path=DB_PATH).exec()

    def _show_questions(self) -> None:
        self._show_page("questions")

    def _show_history(self) -> None:
        self._show_page("history")


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
