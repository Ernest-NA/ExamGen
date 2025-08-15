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

from examgen.config import AppSettings, db_path
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
        self.le_db = QLineEdit(settings.db_folder or "")
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
        path = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta de datos"
        )
        if path:
            self.le_db.setText(path)

    def accept(self) -> None:  # type: ignore[override]
        self.settings.theme = self.cb_theme.currentText()
        import examgen.config as cfg
        self.settings.db_folder = self.le_db.text() or None
        cfg.db_folder = self.settings.db_folder
        self.settings.save()
        if self.settings.db_folder:
            set_engine(db_path())
        super().accept()
