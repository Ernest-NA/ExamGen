from PySide6.QtWidgets import QApplication, QLabel, QMainWindow
from PySide6.QtCore import Qt
import sys

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ExamGen")
        self.resize(600, 400)
        label = QLabel("Hello ExamGen", alignment=Qt.AlignCenter)
        self.setCentralWidget(label)

def main() -> None:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
