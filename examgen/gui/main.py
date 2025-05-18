"""examgen/gui/main.py – Entry‑point de la interfaz gráfica.

• Detecta / crea el directorio de datos con examgen.config
• Si no hay BD configurada muestra UI mínima con botón «Localizar BBDD…»
• Si hay BD → migración, registro o login y UI completa (sin reiniciar)
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QFont
from PySide6.QtWidgets import QDialog 
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QMenuBar,
    QStatusBar,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

from examgen import config, models, auth
from examgen.gui.dialogs import QuestionDialog
from examgen.gui.style import Style
from examgen.gui import login, register, settings

# ─────────────────────────── Directorio de datos ───────────────────────────
DATA_DIR: Path | None = config.get_data_dir(ask_user=False)
DB_PATH:  Path | None = (DATA_DIR / "examgen.db") if DATA_DIR else None
MISSING_DB: bool = DATA_DIR is None

engine: models.Engine | None = None   # se asigna cuando exista BD
CURRENT_USER: auth.User | None = None # idem



# -------------------------------------------------------------------------
# Función auxiliar: bootstrapping completo
# -------------------------------------------------------------------------

def _bootstrap_db(path: Path) -> bool:
    """Inicializa BD, registro/login y tema.

    Devuelve True si el flujo finaliza con un usuario autenticado; False si se
    canceló.
    """
    global engine, CURRENT_USER, DB_PATH, DATA_DIR, MISSING_DB  # pylint: disable=global-statement

    DATA_DIR = path
    DB_PATH = path / "examgen.db"
    MISSING_DB = False

    models.init_db(DB_PATH)
    engine = models.get_engine(DB_PATH)

    # registro o login
    with models.Session(engine) as s:
        has_users = s.query(auth.User).first() is not None

    if not has_users:
        dlg = register.RegisterDialog(db_path=DB_PATH, parent=None)
        if dlg.exec() != QDialog.Accepted:         # ← aquí
            return False
        CURRENT_USER = dlg.user
    else:
        dlg = login.LoginDialog(db_path=DB_PATH, parent=None)
        if dlg.exec() != QDialog.Accepted:         # ← y aquí
            return False
        CURRENT_USER = dlg.user

    Style.apply(CURRENT_USER.theme)
    return True

# -------------------------------------------------------------------------
# Bootstrapping inmediato si la carpeta ya existía
# -------------------------------------------------------------------------



# ─────────────────────────── Ventana principal ─────────────────────────────
class MainWindow(QMainWindow):
    """Ventana principal de ExamGen."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ExamGen")
        self.resize(1280, 720)

        if MISSING_DB:
            self._setup_no_db_ui()
        else:
            self._normal_startup()

    # ------------------------ modo sin BD ---------------------------
    def _setup_no_db_ui(self) -> None:
        msg = QLabel(
            "Aún no has indicado dónde guardar la base de datos.",
            alignment=Qt.AlignCenter,
        )
        btn = QPushButton("Localizar BBDD…", clicked=self._choose_data_dir)
        btn.setFixedWidth(220)

        box = QWidget()
        vbox = QVBoxLayout(box)
        vbox.addStretch(1)
        vbox.addWidget(msg)
        hbox = QHBoxLayout(); hbox.addStretch(1); hbox.addWidget(btn); hbox.addStretch(1)
        vbox.addLayout(hbox)
        vbox.addStretch(1)
        self.setCentralWidget(box)

        mb = QMenuBar(self); self.setMenuBar(mb)
        mb.addAction("Localizar BBDD…", self._choose_data_dir)
        mb.addAction("Salir", QApplication.instance().quit)

    def _choose_data_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Selecciona carpeta para la BBDD")
        if not folder:
            return
        path = Path(folder)
        config.set_data_dir(path)
        path.mkdir(parents=True, exist_ok=True)

        if not _bootstrap_db(path):
            return  # registro/login cancelado

        QMessageBox.information(self, "Configurado", "Se ha creado la base de datos en la ubicación seleccionada.")
        self.menuBar().clear()
        self._normal_startup()

    # ------------------------ modo normal ---------------------------
    def _normal_startup(self) -> None:
        self.setCentralWidget(
            QLabel(f"Bienvenido, {CURRENT_USER.username}", alignment=Qt.AlignCenter)
        )
        self._create_menu_bar()
        self._create_status_bar()
        self._update_status()

    # ------------------------ menús ------------------------------
    def _create_menu_bar(self) -> None:
        mb = QMenuBar(self); self.setMenuBar(mb)

        # Archivo
        m_arch = mb.addMenu("&Archivo")
        m_arch.addAction("Nueva &pregunta…", self._new_question)
        m_arch.addSeparator()
        m_arch.addAction("Cambiar &BD…", self._change_db)
        m_arch.addSeparator()
        m_arch.addAction("Salir", QApplication.instance().quit)

        # Tema
        m_tema = mb.addMenu("&Tema")
        grp = QActionGroup(self, exclusive=True)
        for key, label in (("light", "Claro"), ("dark", "Oscuro")):
            act = QAction(label, self, checkable=True)
            act.setChecked(CURRENT_USER and key == CURRENT_USER.theme)
            act.triggered.connect(lambda _=False, k=key: self._switch_theme(k))
            grp.addAction(act); m_tema.addAction(act)

        # Ajustes
        mb.addMenu("&Ajustes").addAction("Preferencias…", self._open_settings)

    # ------------------------ barra de estado ----------------------
    def _create_status_bar(self) -> None:
        self.setStatusBar(QStatusBar(self))

    def _update_status(self) -> None:
        if engine is None:
            return
        with models.Session(engine) as s:
            subs = s.query(models.Subject).count()
            ques = s.query(models.Question).count()
        self.statusBar().showMessage(
            f"Materias: {subs}   Preguntas: {ques}   BD: {DB_PATH}")

    # ------------------------ acciones -----------------------------
    def _new_question(self):
        if QuestionDialog(self, db_path=DB_PATH).exec():
            self._update_status()

    def _switch_theme(self, key: str):
        if not CURRENT_USER or key == CURRENT_USER.theme:
            return
        CURRENT_USER.theme = key
        with models.Session(engine) as s:
            s.merge(CURRENT_USER); s.commit()
        Style.apply(key)

    def _open_settings(self):
        if CURRENT_USER:
            settings.SettingsDialog(user=CURRENT_USER, db_path=DB_PATH, parent=self).exec()

    def _change_db(self):
        new, _ = QFileDialog.getExistingDirectory(self, "Selecciona nueva carpeta de BD")
        if new:
            QMessageBox.information(self, "Info", "Reinicia la aplicación y selecciona la nueva BD.")


# ───────────────────────── entry‑point ───────────────────────────────

def main() -> None:
    app = QApplication(sys.argv)
    f = QFont(); f.setPointSize(11); app.setFont(f)

    # bootstrapping ahora que QApplication existe
    global MISSING_DB  # si la cambias dentro de main
    if not MISSING_DB:
        _bootstrap_db(DATA_DIR)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())



if __name__ == "__main__":
    main()
