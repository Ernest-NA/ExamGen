from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QStandardPaths, Qt
from PySide6.QtWidgets import (
    QWidget,
    QComboBox,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from examgen.core.settings import AppSettings
from examgen.core.database import set_engine

if TYPE_CHECKING:  # pragma: no cover - circular imports only for type hints
    from examgen.gui.windows.main_window import MainWindow  # noqa: F401


class SettingsPage(QWidget):
    """Editable application settings as a page."""

    def __init__(
        self, settings: AppSettings, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.settings = settings

        self.cb_theme = QComboBox()
        self.cb_theme.addItems(["dark", "light"])
        self.cb_theme.setCurrentText(settings.theme)

        self.chk_debug = QCheckBox("Activar modo depuración")
        self.chk_debug.setChecked(settings.debug_mode)

        self.le_db = QLineEdit(settings.data_db_path or "")
        self.le_db.setReadOnly(True)
        btn_choose = QPushButton("Elegir…", clicked=self._choose_db)
        btn_save = QPushButton("Guardar", clicked=self.save_settings)

        form = QFormLayout()
        form.addRow("Tema:", self.cb_theme)
        hb = QHBoxLayout()
        hb.addWidget(self.le_db)
        hb.addWidget(btn_choose)
        form.addRow("Base de datos:", hb)
        form.addRow(self.chk_debug)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(btn_save, alignment=Qt.AlignRight)

    # ------------------------------------------------------------------
    def _choose_db(self) -> None:
        start_dir = (
            Path(self.settings.data_db_path).parent
            if self.settings.data_db_path
            else Path(
                QStandardPaths.writableLocation(
                    QStandardPaths.DocumentsLocation
                )
            )
        )
        path = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta de datos",
            str(start_dir),
        )
        if not path:
            return
        self.le_db.setText(str(Path(path) / "examgen.db"))

    def save_settings(self) -> None:
        self.settings.theme = self.cb_theme.currentText()
        self.settings.data_db_path = self.le_db.text() or None
        self.settings.debug_mode = self.chk_debug.isChecked()
        self.settings.save()
        if self.settings.data_db_path:
            set_engine(Path(self.settings.data_db_path))
        win = self.window()
        from examgen.gui.windows.main_window import MainWindow as MW

        if isinstance(win, MW):
            win._apply_theme()
            win._set_app_actions_enabled(bool(self.settings.data_db_path))
