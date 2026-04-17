import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox,
)


class ReportsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._word_path  = ""
        self._excel_path = ""
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(20)

        title = QLabel("דוחות")
        title.setObjectName("section_title")
        layout.addWidget(title)

        # Word report
        word_group = QGroupBox("דוח Word (יומן עיבוד)")
        word_layout = QHBoxLayout(word_group)
        self.word_path_label = QLabel("טרם נוצר דוח")
        self.word_path_label.setWordWrap(True)
        self.open_word_btn = QPushButton("פתח")
        self.open_word_btn.setEnabled(False)
        self.open_word_btn.clicked.connect(self._open_word)
        word_layout.addWidget(self.word_path_label, 1)
        word_layout.addWidget(self.open_word_btn)
        layout.addWidget(word_group)

        # Excel report
        excel_group = QGroupBox("דוח Excel (רשימת מסמכים)")
        excel_layout = QHBoxLayout(excel_group)
        self.excel_path_label = QLabel("טרם נוצר דוח")
        self.excel_path_label.setWordWrap(True)
        self.open_excel_btn = QPushButton("פתח")
        self.open_excel_btn.setEnabled(False)
        self.open_excel_btn.clicked.connect(self._open_excel)
        excel_layout.addWidget(self.excel_path_label, 1)
        excel_layout.addWidget(self.open_excel_btn)
        layout.addWidget(excel_group)

        # Open reports folder
        folder_btn = QPushButton("פתח תיקיית דוחות")
        folder_btn.setObjectName("btn_secondary")
        folder_btn.clicked.connect(self._open_reports_folder)
        layout.addWidget(folder_btn, alignment=Qt.AlignmentFlag.AlignRight)

        layout.addStretch()

    def update_paths(self, word_path: str, excel_path: str):
        self._word_path  = word_path
        self._excel_path = excel_path
        if word_path:
            self.word_path_label.setText(word_path)
            self.open_word_btn.setEnabled(True)
        if excel_path:
            self.excel_path_label.setText(excel_path)
            self.open_excel_btn.setEnabled(True)

    def _open_word(self):
        if self._word_path and os.path.exists(self._word_path):
            os.startfile(self._word_path)

    def _open_excel(self):
        if self._excel_path and os.path.exists(self._excel_path):
            os.startfile(self._excel_path)

    def _open_reports_folder(self):
        from core.reporter import REPORTS_DIR
        os.makedirs(REPORTS_DIR, exist_ok=True)
        os.startfile(REPORTS_DIR)
