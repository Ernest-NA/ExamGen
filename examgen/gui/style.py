"""examgen.gui.style – Theme definitions and helpers.

Provides two stylesheets (Light / Dark) and a convenient ``Style.apply()``
method to change the application theme at runtime.
"""
from __future__ import annotations

from PySide6.QtWidgets import QApplication


class Style:  # pylint: disable=too-few-public-methods
    """Central place for UI themes."""

    # ---------------------------- Light theme ----------------------------
    LIGHT = """
    * { font-family: 'Segoe UI', 'San Francisco', Arial, sans-serif; font-size: 14px; }
    QPushButton {
        border: 1px solid #2e7d32;
        border-radius: 6px;
        padding: 4px 10px;
        background-color: #43a047;
        color: white;
    }
    QPushButton:hover  { background-color: #388e3c; }
    QPushButton:pressed{ background-color: #2e7d32; }
    QHeaderView::section {
        background-color: #eeeeee;
        padding: 4px;
        border: 1px solid #cccccc;
        font-weight: bold;
    }
    QTableWidget QTableCornerButton::section {
        background: #eeeeee;
        border: 1px solid #cccccc;
    }
    """

    # ---------------------------- Dark theme -----------------------------
    DARK = """
    * { font-family: 'Segoe UI', 'San Francisco', Arial, sans-serif; font-size: 14px; color: #dcdcdc; background-color: #202124; }
    QPushButton {
        border: 1px solid #4caf50;
        border-radius: 6px;
        padding: 4px 10px;
        background-color: #388e3c;
        color: white;
    }
    QPushButton:hover  { background-color: #2e7d32; }
    QPushButton:pressed{ background-color: #1b5e20; }
    QHeaderView::section {
        background-color: #303134;
        padding: 4px;
        border: 1px solid #5f6368;
        font-weight: bold;
        color: #e8eaed;
    }
    QTableWidget QTableCornerButton::section {
        background: #303134;
        border: 1px solid #5f6368;
    }
    QLineEdit, QPlainTextEdit, QComboBox, QTableWidget {
        background-color: #2b2b2b;
        color: #dcdcdc;
        selection-background-color: #4a90e2;
    }
    """

    # Map clave interna (minúscula) → stylesheet
    THEMES = {
        "light": LIGHT,
        "dark": DARK,
        # alias en español para compatibilidad
        "claro": LIGHT,
        "oscuro": DARK,
    }

    # ------------------------------------------------------------------
    @classmethod
    def sheet(cls, theme: str) -> str:  # noqa: D401
        """Devuelve la hoja de estilo de *theme*; por defecto LIGHT."""
        return cls.THEMES.get(theme.lower(), cls.LIGHT)

    @classmethod
    def apply(cls, theme: str = "dark") -> None:
        """Aplica la hoja de estilo *theme* al QApplication actual."""
        app = QApplication.instance()
        if app is None:
            return  # no hay app (ej.: tests CLI)
        app.setStyleSheet(cls.sheet(theme))
