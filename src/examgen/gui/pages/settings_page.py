from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
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

from examgen.config import AppSettings, db_path
from examgen.utils.debug import log
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
        self.chk_debug.stateChanged.connect(self._on_debug_toggled)

        self.dir_edit = QLineEdit(settings.db_folder or "")
        self.dir_edit.setReadOnly(True)
        btn_choose = QPushButton("…", clicked=self._pick_db_dir)
        btn_save = QPushButton("Guardar", clicked=self.save_settings)

        form = QFormLayout()
        form.addRow("Tema:", self.cb_theme)
        hb = QHBoxLayout()
        hb.addWidget(self.dir_edit)
        hb.addWidget(btn_choose)
        form.addRow("Base de datos:", hb)
        form.addRow(self.chk_debug)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(btn_save, alignment=Qt.AlignRight)

    # ------------------------------------------------------------------
    def _pick_db_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta para BD"
        )
        if d:
            self.dir_edit.setText(d)

    def save_settings(self) -> None:
        import examgen.config as cfg

        self.settings.theme = self.cb_theme.currentText()
        self.settings.db_folder = self.dir_edit.text() or None
        self.settings.debug_mode = self.chk_debug.isChecked()
        self.settings.save()
        cfg.db_folder = self.settings.db_folder
        set_engine(db_path())
        win = self.window()
        from examgen.gui.windows.main_window import MainWindow as MW

        if isinstance(win, MW):
            win._apply_theme()
            win._set_app_actions_enabled(bool(self.settings.db_folder))

    def _on_debug_toggled(self, state: int) -> None:
        self.settings.debug_mode = bool(state)
        from examgen.utils.logger import set_logging

        set_logging()
        log(
            f"Modo depuraci\u00f3n {'activo' if state else 'inactivo'}"
        )
