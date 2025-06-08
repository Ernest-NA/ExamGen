from __future__ import annotations

import sys

from pathlib import Path

from PySide6.QtWidgets import QApplication

from examgen.core.database import get_engine, init_db, set_engine
from examgen.core.settings import AppSettings


st = AppSettings.load()
db_path = Path(st.data_db_path or Path.home() / "Documents" / "examgen.db")
db_path.parent.mkdir(parents=True, exist_ok=True)
set_engine(db_path)
if db_path.exists() or st.data_db_path is None:
    init_db(get_engine())


def main() -> None:
    """Punto de entrada principal de la GUI."""
    # Importar dentro de la función para evitar ciclos
    from examgen.gui.windows.main_window import MainWindow

    app = QApplication.instance() or QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


__all__ = ["main"]
