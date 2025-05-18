"""examgen/gui/register.py – Diálogo de registro de usuario

Solicita *username*, *email* y contraseña (dos veces).
Devuelve ``self.user`` (instancia de ``auth.User``) cuando el usuario pulsa
«Registrar» con datos válidos (acepta el diálogo).  Si el usuario cancela o
hay validación errónea, el diálogo se cierra con ``Rejected`` y ``self.user``
es ``None``.
"""
from __future__ import annotations

import re
import hashlib
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from sqlalchemy.orm import Session

from examgen import models, auth

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z0-9]{2,}$")

# simple hash → en producción usa bcrypt/argon2 -----------------------------

def _hash_password(pwd: str) -> str:
    return hashlib.sha256(pwd.encode("utf-8")).hexdigest()


class RegisterDialog(QDialog):
    """Diálogo de registro.  Uso::

        dlg = RegisterDialog(db_path)
        if dlg.exec() == QDialog.Accepted:
            user = dlg.user  # instancia auth.User
    """

    def __init__(self, db_path: Path | str, parent=None) -> None:  # noqa: D401
        super().__init__(parent)
        self.setWindowTitle("Crear cuenta")
        self.setModal(True)
        self.user: auth.User | None = None

        # --- widgets ---------------------------------------------------
        self._le_username = QLineEdit();  self._le_username.setMaxLength(40)
        self._le_email    = QLineEdit();  self._le_email.setMaxLength(320)
        self._le_pass1    = QLineEdit();  self._le_pass1.setEchoMode(QLineEdit.Password)
        self._le_pass2    = QLineEdit();  self._le_pass2.setEchoMode(QLineEdit.Password)

        form = QFormLayout()
        form.addRow("Usuario:",   self._le_username)
        form.addRow("Email:",     self._le_email)
        form.addRow("Contraseña:", self._le_pass1)
        form.addRow("Repite contraseña:", self._le_pass2)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(buttons)

        # engine y sesión ---------------------------------------------
        self._engine = models.get_engine(db_path)

    # ------------------------------------------------------------------
    def _on_accept(self) -> None:  # noqa: D401
        usr = self._le_username.text().strip()
        email = self._le_email.text().strip().lower()
        pwd1 = self._le_pass1.text()
        pwd2 = self._le_pass2.text()

        if not usr or not email or not pwd1:
            QMessageBox.warning(self, "Campos vacíos", "Completa todos los campos.")
            return
        if not EMAIL_RE.match(email):
            QMessageBox.warning(self, "Email no válido", "Introduce un email válido.")
            return
        if pwd1 != pwd2:
            QMessageBox.warning(self, "Contraseñas", "Las contraseñas no coinciden.")
            return
        if len(pwd1) < 6:
            QMessageBox.warning(self, "Contraseña", "Debe contener al menos 6 caracteres.")
            return

        # comprobar unicidad de usuario / email ------------------------
        with Session(self._engine) as s:
            if s.query(auth.User).filter_by(username=usr).first():
                QMessageBox.warning(self, "Usuario existente", "El nombre ya está en uso.")
                return
            if s.query(auth.User).filter_by(email=email).first():
                QMessageBox.warning(self, "Email existente", "Ese email ya está registrado.")
                return

            self.user = auth.User(
                username=usr,
                email=email,
                password_hash=_hash_password(pwd1),
                theme="dark",
            )
            s.add(self.user)
            s.commit()

        self.accept()
