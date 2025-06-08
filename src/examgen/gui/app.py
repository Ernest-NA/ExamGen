from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication


def main() -> None:
    """Punto de entrada principal de la GUI."""
    # Importar dentro de la función para evitar ciclos
    from examgen.gui.windows.main_window import MainWindow

    app = QApplication.instance() or QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


__all__ = ["main"]
