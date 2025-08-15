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

OPTION_EXPL_STYLE = """
QLabel#OptExplanation {
    color: #b5b5b5;
    font-style: italic;
    margin-left: 28px;
    margin-bottom: 8px;
}
"""

EXPLANATION_BOX_STYLE = """
QFrame#explanationBox {
    border: 1px solid #4caf50;
    background: #1a1a1a;
    border-radius: 4px;
    padding: 4px 8px;
}
QLabel#explanationLabel { color: #4caf50; }
"""


def apply_app_styles(app: QApplication) -> None:
    """Apply global styles to *app*."""
    app.setStyleSheet(BUTTON_STYLE + OPTION_EXPL_STYLE + EXPLANATION_BOX_STYLE)
