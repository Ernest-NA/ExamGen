"""examgen/config.py – Selección y persistencia del directorio de datos.
------------------------------------------------------------------------
Guarda la ruta elegida en un fichero INI:
  • Linux/macOS → ~/.config/examgen.ini
  • Windows     → %APPDATA%\ExamGen\config.ini

Exporta:
    get_data_dir()  -> Path  # ruta final, preguntando si falta
    ensure_db_dir() -> Path  # idem y crea carpeta si no existe

Requiere PySide6 si se llama con ask_user=True.
"""
from __future__ import annotations

import os
import platform
import sys
from configparser import ConfigParser
from pathlib import Path
from typing import Optional

SETTINGS_SECTION = "examgen"
SETTINGS_KEY     = "data_dir"

# ---------------------------------------------------------------------
# Helpers ruta del archivo INI dependiendo del SO
# ---------------------------------------------------------------------

def _settings_path() -> Path:
    if platform.system() == "Windows":
        base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming")) / "ExamGen"
    else:
        base = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))
    base.mkdir(parents=True, exist_ok=True)
    return base / "examgen.ini"


# ---------------------------------------------------------------------
# Cargar / guardar config
# ---------------------------------------------------------------------

def _load_config() -> ConfigParser:
    cfg = ConfigParser()
    cfg.read(_settings_path())
    return cfg


def _save_config(cfg: ConfigParser) -> None:
    with _settings_path().open("w", encoding="utf-8") as fp:
        cfg.write(fp)

# ---------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------

def get_data_dir(*, ask_user: bool = True) -> Optional[Path]:
    """Devuelve la ruta del directorio de datos.

    Si no está configurado y ask_user=True, muestra un diálogo para escoger.
    Retorna None si no se pudo determinar (cancelado).
    """
    cfg = _load_config()
    if cfg.has_option(SETTINGS_SECTION, SETTINGS_KEY):
        return Path(cfg.get(SETTINGS_SECTION, SETTINGS_KEY)).expanduser()

    if not ask_user:
        return None

    # --- Preguntar al usuario con QFileDialog -------------------------
    try:
        from PySide6.QtWidgets import QFileDialog, QApplication
    except ImportError:  # fallback CLI
        path_str = input("Directorio para los datos de ExamGen: ").strip()
        path = Path(path_str).expanduser()
    else:
        # Si no hay un QApplication, créalo en modo local
        app_created = False
        if not QApplication.instance():
            _ = QApplication(sys.argv)
            app_created = True
        path_str = QFileDialog.getExistingDirectory(None, "Elige directorio para los datos de ExamGen")
        path = Path(path_str) if path_str else Path()
        if app_created:
            QApplication.instance().quit()

    if not path or not path.exists():
        return None

    cfg.setdefault(SETTINGS_SECTION, {})[SETTINGS_KEY] = str(path)
    _save_config(cfg)
    return path


def ensure_db_dir() -> Path:
    """Devuelve la ruta final y crea la carpeta si no existe."""
    data_dir = get_data_dir()
    if data_dir is None:
        print("❌ No se seleccionó directorio de datos. Abortando…")
        sys.exit(1)
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

def set_data_dir(path: Path) -> None:
    """Guarda definitivamente la ruta del directorio de datos."""
    cfg = _load_config()
    cfg.setdefault(SETTINGS_SECTION, {})[SETTINGS_KEY] = str(path)
    _save_config(cfg)


# ---------------------------------------------------------------------
# Test CLI
# ---------------------------------------------------------------------
if __name__ == "__main__":
    print("Directorio de datos:", get_data_dir())
