from __future__ import annotations

import sys

from pathlib import Path

from PySide6.QtWidgets import QApplication

from examgen.core.database import get_engine, init_db
from examgen.core.settings import AppSettings


st = AppSettings.load()
data_root = Path(st.data_dir or ".")
data_root.mkdir(parents=True, exist_ok=True)
DB_PATH = data_root / "examgen.db"
engine = get_engine(DB_PATH)
init_db(engine)


def main() -> None:
    """Punto de entrada principal de la GUI."""
    # Importar dentro de la función para evitar ciclos
    from examgen.gui.windows.main_window import MainWindow

    app = QApplication.instance() or QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


__all__ = ["main"]
