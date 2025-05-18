from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QLabel, QMessageBox, QPushButton
)
from examgen import auth

class LoginDialog(QDialog):
    def __init__(self, *, db_path, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self._user = None
        self.setWindowTitle("Iniciar sesión")

        self.le_user = QLineEdit(); self.le_user.setPlaceholderText("usuario")
        self.le_pwd  = QLineEdit(); self.le_pwd.setEchoMode(QLineEdit.Password)

        form = QFormLayout(self)
        form.addRow("Usuario:", self.le_user)
        form.addRow("Contraseña:", self.le_pwd)

        btn_reset = QPushButton("Olvidé contraseña", clicked=self._reset_pwd)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
                                accepted=self._login, rejected=self.reject)
        form.addRow(btn_reset, btns)

    # ---- getters ----
    def exec(self):
        if super().exec() == self.Accepted:
            return self._user
        return None

    # ---- acciones ----
    def _login(self):
        u = auth.login(self.le_user.text(), self.le_pwd.text(), db_path=self.db_path)
        if not u:
            QMessageBox.warning(self, "Error", "Credenciales incorrectas.")
            return
        self._user = u
        self.accept()

    def _reset_pwd(self):
        from examgen.gui.reset_pwd import ResetPasswordDialog
        ResetPasswordDialog(db_path=self.db_path).exec()
