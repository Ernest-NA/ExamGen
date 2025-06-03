"""Application-wide stylesheet utilities."""
from PySide6.QtWidgets import QApplication

BUTTON_STYLE = """
QPushButton {
    background-color: #28a745;          /* verde habilitado */
    color: white;
    border-radius: 4px;
    padding: 4px 12px;
}
QPushButton:disabled {
    background-color: #9e9e9e;          /* gris claro */
    color: #ededed;
}
QDialogButtonBox > QPushButton:disabled {
    background-color: #9e9e9e;          /* gris claro */
    color: #ededed;
}

/* ---- dynamic state colours ---- */
QAbstractButton[state="correct"]  { color: lightgreen; }
QAbstractButton[state="wrong"]    { color: salmon; }
QAbstractButton[state="correct"]::indicator:checked,
QAbstractButton[state="correct"]::indicator:checked:disabled {
    background: lightgreen; border: 1px solid lightgreen;
}
QAbstractButton[state="wrong"]::indicator:checked,
QAbstractButton[state="wrong"]::indicator:checked:disabled {
    background: salmon; border: 1px solid salmon;
}
"""


def apply_app_styles(app: QApplication) -> None:
    """Apply global styles to *app*."""
    app.setStyleSheet(BUTTON_STYLE)
