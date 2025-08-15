from __future__ import annotations

import sys

from pathlib import Path

from PySide6.QtWidgets import QApplication

from examgen.core.database import (
    get_engine,
    init_db,
    run_migrations,
    set_engine,
)
from examgen.config import settings, db_path


db_file = db_path()
db_file.parent.mkdir(parents=True, exist_ok=True)
set_engine(db_file)
run_migrations()
if db_file.exists() or settings.db_folder is None:
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
