from examgen.gui.dialogs import ExamConfigDialog
from examgen.gui.widgets import start_exam
from PySide6.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)

config = ExamConfigDialog.get_config()
if config:
    start_exam(config)
    sys.exit(app.exec())
