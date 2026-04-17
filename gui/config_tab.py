import json
import os

import keyring
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QGroupBox, QFormLayout, QMessageBox,
)

SERVICE_NAME = "קליטה_לחשבשבת"
CONFIG_FILE  = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "config.json")


class ConfigTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._build_ui()
        self._load()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(30, 20, 30, 20)
        outer.setSpacing(20)

        title = QLabel("הגדרות מערכת")
        title.setObjectName("section_title")
        outer.addWidget(title)

        # Credentials group
        creds_group = QGroupBox("פרטי כניסה לחשבשבת")
        creds_layout = QFormLayout(creds_group)
        creds_layout.setSpacing(10)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("שם משתמש")
        creds_layout.addRow("שם משתמש:", self.username_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("סיסמה")
        creds_layout.addRow("סיסמה:", self.password_edit)

        outer.addWidget(creds_group)

        # Folders group
        folders_group = QGroupBox("תיקיות קלט")
        folders_layout = QFormLayout(folders_group)
        folders_layout.setSpacing(10)

        self.invoice_edit, inv_row = self._folder_row("בחר תיקייה…")
        folders_layout.addRow("תיקיית חשבוניות:", inv_row)

        self.receipt_edit, rec_row = self._folder_row("בחר תיקייה…")
        folders_layout.addRow("תיקיית קבלות:", rec_row)

        outer.addWidget(folders_group)

        # Save button
        save_btn = QPushButton("שמור הגדרות")
        save_btn.setObjectName("btn_success")
        save_btn.setFixedWidth(160)
        save_btn.clicked.connect(self._save)
        outer.addWidget(save_btn, alignment=Qt.AlignmentFlag.AlignRight)

        outer.addStretch()

    @staticmethod
    def _folder_row(placeholder: str):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        browse_btn = QPushButton("עיין…")
        browse_btn.setObjectName("btn_secondary")
        browse_btn.setFixedWidth(70)
        browse_btn.clicked.connect(lambda: _browse_folder(edit))
        layout.addWidget(edit)
        layout.addWidget(browse_btn)
        return edit, container

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self.invoice_edit.setText(cfg.get("invoice_folder", ""))
                self.receipt_edit.setText(cfg.get("receipt_folder", ""))
                self.username_edit.setText(cfg.get("username", ""))
            except Exception:
                pass
        try:
            pwd = keyring.get_password(SERVICE_NAME, self.username_edit.text())
            if pwd:
                self.password_edit.setText(pwd)
        except Exception:
            pass

    def _save(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        cfg = {
            "invoice_folder": self.invoice_edit.text().strip(),
            "receipt_folder": self.receipt_edit.text().strip(),
            "username": username,
        }
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        if username and password:
            try:
                keyring.set_password(SERVICE_NAME, username, password)
            except Exception:
                pass
        QMessageBox.information(self, "הגדרות", "ההגדרות נשמרו בהצלחה ✔")

    # ── Public getters ────────────────────────────────────────────────────────

    @property
    def invoice_folder(self) -> str:
        return self.invoice_edit.text().strip()

    @property
    def receipt_folder(self) -> str:
        return self.receipt_edit.text().strip()

    @property
    def username(self) -> str:
        return self.username_edit.text().strip()

    @property
    def password(self) -> str:
        return self.password_edit.text()


def _browse_folder(line_edit: QLineEdit):
    folder = QFileDialog.getExistingDirectory(None, "בחר תיקייה")
    if folder:
        line_edit.setText(folder)
