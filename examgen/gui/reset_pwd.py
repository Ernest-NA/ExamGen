"""ResetPasswordDialog – permite cambiar la contraseña de un usuario existente.

Invocado desde LoginDialog cuando el usuario no recuerda su contraseña.
Requiere examgen.auth para verificación y cambio.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLineEdit,
    QDialogButtonBox,
    QMessageBox,
)

from examgen import auth


class ResetPasswordDialog(QDialog):
    """Dialogo simple de cambio de contraseña (sin email)."""

    def __init__(self, *, db_path: str | Path, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.setWindowTitle("Restablecer contraseña")
        self.setModal(True)

        self.le_user = QLineEdit(); self.le_user.setPlaceholderText("usuario")
        self.le_new1 = QLineEdit(); self.le_new1.setEchoMode(QLineEdit.Password)
        self.le_new2 = QLineEdit(); self.le_new2.setEchoMode(QLineEdit.Password)

        form = QFormLayout(self)
        form.addRow("Usuario:", self.le_user)
        form.addRow("Nueva contraseña:", self.le_new1)
        form.addRow("Repite contraseña:", self.le_new2)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel,
                                accepted=self._change, rejected=self.reject)
        form.addRow(btns)

    # --------------------------------------------------------
    def _change(self):
        usr   = self.le_user.text().strip().lower()
        pwd1  = self.le_new1.text()
        pwd2  = self.le_new2.text()

        if not usr or not pwd1:
            QMessageBox.warning(self, "Datos incompletos", "Rellena usuario y contraseña.")
            return
        if pwd1 != pwd2:
            QMessageBox.warning(self, "No coinciden", "Las contraseñas no coinciden.")
            return
        if len(pwd1) < 6:
            QMessageBox.warning(self, "Débil", "Usa al menos 6 caracteres.")
            return

        engine = auth.get_engine(self.db_path)
        with auth.Session(engine) as s:  # type: ignore[attr-defined]
            u = s.query(auth.User).filter_by(username=usr).first()
            if not u:
                QMessageBox.warning(self, "No encontrado", "Ese usuario no existe.")
                return
            u.set_password(pwd1)
            s.commit()
        QMessageBox.information(self, "Contraseña actualizada", "La contraseña se ha cambiado.")
        self.accept()
