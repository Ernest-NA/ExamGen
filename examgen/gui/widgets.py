from __future__ import annotations
from typing import List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QTableWidget, QTableWidgetItem

from examgen import models as m


class OptionTable(QTableWidget):
    """Table with text column and a checkable 'Correcta' column."""

    def __init__(self, rows: int = 4, parent: QDialog | None = None):
        super().__init__(rows, 2, parent)
        self.setHorizontalHeaderLabels(["Opción", "Correcta"])
        self.horizontalHeader().setStretchLastSection(True)
        self.setColumnWidth(0, 340)
        self.setColumnWidth(1, 90)
        self._populate_checkboxes()

    def _populate_checkboxes(self) -> None:
        for row in range(self.rowCount()):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Unchecked)
            self.setItem(row, 1, chk)

    def collect_options(self) -> tuple[List[m.AnswerOption], int]:
        """Return list of AnswerOption and number of correct answers."""
        opts: List[m.AnswerOption] = []
        correct = 0
        for r in range(self.rowCount()):
            txt_item = self.item(r, 0)
            if not txt_item or not txt_item.text().strip():
                continue
            chk_item = self.item(r, 1)
            is_corr = chk_item.checkState() == Qt.CheckState.Checked if chk_item else False
            if is_corr:
                correct += 1
            opts.append(m.AnswerOption(text=txt_item.text().strip(), is_correct=is_corr))
        return opts, correct
