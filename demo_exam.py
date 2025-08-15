from examgen.gui.dialogs.question_dialog import ExamConfigDialog
from examgen.gui.widgets.option_table import start_exam
from PySide6.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)

config = ExamConfigDialog.get_config()
if config:
    start_exam(config)
    sys.exit(app.exec())