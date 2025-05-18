from __future__ import annotations
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QRadioButton, QVBoxLayout,
    QGroupBox, QLabel, QPushButton, QMessageBox
)
from examgen import auth
from examgen.gui.reset_pwd import ResetPasswordDialog
from examgen.gui.style import Style


class SettingsDialog(QDialog):
    """Preferencias de usuario: tema y cambio de contraseña."""

    def __init__(self, *, user: auth.User, db_path: Path, parent=None) -> None:
        super().__init__(parent)
        self.user = user
        self.db_path = db_path
        self.setWindowTitle("Ajustes")

        # --- selector de tema -------------------------------------------
        grp_theme = QGroupBox("Tema")
        self.rb_light = QRadioButton("Claro")
        self.rb_dark  = QRadioButton("Oscuro")
        if user.theme == "light":
            self.rb_light.setChecked(True)
        else:
            self.rb_dark.setChecked(True)
        vtheme = QVBoxLayout(grp_theme)
        vtheme.addWidget(self.rb_light)
        vtheme.addWidget(self.rb_dark)

        # --- cambio de contraseña ---------------------------------------
        lbl_pwd = QLabel("Cambiar la contraseña de la cuenta:")
        btn_pwd = QPushButton("Cambiar contraseña…", clicked=self._change_pwd)

        # --- botones ----------------------------------------------------
        btns = QDialogButtonBox(QDialogButtonBox.Close, rejected=self.reject)

        # --- layout raíz ------------------------------------------------
        root = QVBoxLayout(self)
        root.addWidget(grp_theme)
        root.addSpacing(10)
        root.addWidget(lbl_pwd)
        root.addWidget(btn_pwd)
        root.addStretch(1)
        root.addWidget(btns)

        # señales
        self.rb_light.toggled.connect(self._apply_theme)
        self.rb_dark.toggled.connect(self._apply_theme)

    # ------------------------------------------------------------------ #
    #  Slots                                                             #
    # ------------------------------------------------------------------ #
    def _apply_theme(self) -> None:
        new_theme = "light" if self.rb_light.isChecked() else "dark"
        if new_theme != self.user.theme:
            self.user.theme = new_theme
            with auth.Session(auth.get_engine(self.db_path)) as s:
                s.merge(self.user)
                s.commit()
            Style.apply(new_theme)
            QMessageBox.information(self, "Tema actualizado",
                                     f"Se ha aplicado el tema {new_theme.capitalize()}.")

    def _change_pwd(self) -> None:
        ResetPasswordDialog(db_path=self.db_path, username=self.user.username, parent=self).exec()
