from __future__ import annotations

"""examgen.gui.main – Main window with runtime theme switching."""

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QAction, QActionGroup
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QMenu, QMenuBar

from examgen.gui.style import Style
from examgen.gui.dialogs import QuestionDialog, DB_PATH
from examgen import models as m


class MainWindow(QMainWindow):
    """Main ExamGen window."""

    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self._app = app
        self.current_theme = "Claro"

        self.setWindowTitle("ExamGen")
        self.resize(1280, 720)

        label = QLabel("Hello ExamGen", alignment=Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(label)

        self._build_menus()
        self.refresh_subject_count()

    # ------------------------------------------------------------------
    def _build_menus(self) -> None:
        menubar: QMenuBar = self.menuBar()

        # Archivo
        archivo: QMenu = menubar.addMenu("&Archivo")
        archivo.addAction("Nueva &pregunta…", self.open_question_dialog)
        archivo.addSeparator()
        archivo.addAction("Salir", QApplication.instance().quit)

        # Tema
        tema: QMenu = menubar.addMenu("&Tema")
        act_group = QActionGroup(self, exclusive=True)
        for name in Style.THEMES.keys():
            act = QAction(name, self, checkable=True)
            if name == self.current_theme:
                act.setChecked(True)
            act.triggered.connect(lambda _=False, n=name: self.set_theme(n))
            act_group.addAction(act)
            tema.addAction(act)

    # ------------------------------------------------------------------
    def set_theme(self, theme: str) -> None:
        self.current_theme = theme
        self._app.setStyleSheet(Style.sheet(theme))

    def open_question_dialog(self) -> None:
        if QuestionDialog(self).exec():
            self.refresh_subject_count()

    def refresh_subject_count(self) -> None:
        try:
            with m.Session(m.get_engine(DB_PATH)) as s:
                total = s.query(m.Subject).count()
        except Exception:
            total = "?"
        self.statusBar().showMessage(f"Materias: {total}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Application entry point."""
    m.init_db(DB_PATH)

    app = QApplication(sys.argv)
    app.setStyleSheet(Style.sheet("Claro"))

    font = QFont()
    font.setPointSize(11)
    app.setFont(font)

    win = MainWindow(app)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
