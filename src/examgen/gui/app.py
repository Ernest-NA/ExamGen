from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from examgen.gui.windows.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


__all__ = ["main"]
