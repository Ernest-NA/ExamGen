from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from examgen.config import AppSettings, DEFAULT_DB
from examgen.core.database import set_engine


class SettingsDialog(QDialog):
    """Dialog to edit application settings."""

    def __init__(self, settings: AppSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configuración")
        self.settings = settings

        # --- Campo Tema ---
        self.cb_theme = QComboBox()
        self.cb_theme.addItems(["dark", "light"])
        self.cb_theme.setCurrentText(settings.theme)

        # --- Campo BD ---
        self.le_db = QLineEdit(settings.data_db_path or "")
        self.le_db.setReadOnly(True)
        btn_choose = QPushButton("Elegir…", clicked=self._choose_db)

        form = QFormLayout()
        form.addRow("Tema:", self.cb_theme)
        hb = QHBoxLayout()
        hb.addWidget(self.le_db)
        hb.addWidget(btn_choose)
        form.addRow("Base de datos:", hb)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(buttons)

    def _choose_db(self) -> None:
        start_dir = (
            Path(self.settings.data_db_path).parent
            if self.settings.data_db_path
            else Path(QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation))
        )
        path = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta de datos",
            str(start_dir),
        )
        if not path:
            return
        self.le_db.setText(str(Path(path) / DEFAULT_DB.name))

    def accept(self) -> None:  # type: ignore[override]
        self.settings.theme = self.cb_theme.currentText()
        self.settings.data_db_path = self.le_db.text() or None
        self.settings.save()
        if self.settings.data_db_path:
            set_engine(Path(self.settings.data_db_path))
        super().accept()
