from PySide6.QtWidgets import QApplication, QLabel, QMainWindow
from PySide6.QtCore import Qt
import sys

class MainWindow(QMainWindow):
    """Ventana principal de ExamGen."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ExamGen")
        # Centrar un texto sencillo
        label = QLabel("Hello ExamGen")
        label.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(label)
        # Tamaño de arranque
        self.resize(600, 400)


def main() -> None:
    """Punto de entrada de la aplicación."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()