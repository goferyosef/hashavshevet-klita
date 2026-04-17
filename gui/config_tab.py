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

        # ── API credentials ────────────────────────────────────────────────
        api_group = QGroupBox("פרטי API של חשבשבת")
        api_layout = QFormLayout(api_group)
        api_layout.setSpacing(10)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText("WizCloud API Private Key")
        api_layout.addRow("API Private Key:", self.api_key_edit)

        self.db_name_edit = QLineEdit()
        self.db_name_edit.setPlaceholderText("שם מסד הנתונים, לדוגמה: wizdb12n12")
        api_layout.addRow("DB Name:", self.db_name_edit)

        self.server_edit = QLineEdit()
        self.server_edit.setPlaceholderText("לדוגמה: lb1.wizcloud.co.il")
        self.server_edit.setText("lb1.wizcloud.co.il")
        api_layout.addRow("Server:", self.server_edit)

        hint = QLabel(
            'כיצד לקבל את המפתח: היכנס לחשבשבת → הגדרות → API → '
            '"מפתח פרטי". אם לא מופיע — פנה לתמיכת WizCloud.'
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #7F8C8D; font-size: 11px;")
        api_layout.addRow("", hint)

        outer.addWidget(api_group)

        # ── Web credentials (for Playwright file attachment) ───────────────
        web_group = QGroupBox("פרטי כניסה לאתר (לצירוף קבצים)")
        web_layout = QFormLayout(web_group)
        web_layout.setSpacing(10)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("שם משתמש")
        web_layout.addRow("שם משתמש:", self.username_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("סיסמה")
        web_layout.addRow("סיסמה:", self.password_edit)

        outer.addWidget(web_group)

        # ── Account codes ──────────────────────────────────────────────────
        acc_group = QGroupBox('קודי חשבונות ברירת מחדל')
        acc_layout = QFormLayout(acc_group)
        acc_layout.setSpacing(10)

        self.vat_account_edit = QLineEdit()
        self.vat_account_edit.setPlaceholderText('לדוגמה: 1315')
        acc_layout.addRow('חשבון מע"מ תשומות:', self.vat_account_edit)

        self.default_expense_edit = QLineEdit()
        self.default_expense_edit.setPlaceholderText('לדוגמה: 8500')
        acc_layout.addRow('חשבון הוצאות ברירת מחדל:', self.default_expense_edit)

        acc_note = QLabel(
            'קודים אלה ישמשו כשלספק אין קוד משלו. '
            'ניתן לעקוף לכל ספק בנפרד בלשונית "ספקים".'
        )
        acc_note.setWordWrap(True)
        acc_note.setStyleSheet("color: #7F8C8D; font-size: 11px;")
        acc_layout.addRow("", acc_note)

        outer.addWidget(acc_group)

        # ── Folders ────────────────────────────────────────────────────────
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
                self.db_name_edit.setText(cfg.get("db_name", ""))
                self.server_edit.setText(cfg.get("server", "lb1.wizcloud.co.il"))
                self.vat_account_edit.setText(cfg.get("vat_account", ""))
                self.default_expense_edit.setText(cfg.get("default_expense_account", ""))
            except Exception:
                pass
        # Load secrets from keyring
        username = self.username_edit.text()
        try:
            api_key = keyring.get_password(SERVICE_NAME, "api_key")
            if api_key:
                self.api_key_edit.setText(api_key)
            pwd = keyring.get_password(SERVICE_NAME, username or "user")
            if pwd:
                self.password_edit.setText(pwd)
        except Exception:
            pass

    def _save(self):
        username = self.username_edit.text().strip()
        cfg = {
            "invoice_folder":          self.invoice_edit.text().strip(),
            "receipt_folder":          self.receipt_edit.text().strip(),
            "username":                username,
            "db_name":                 self.db_name_edit.text().strip(),
            "server":                  self.server_edit.text().strip(),
            "vat_account":             self.vat_account_edit.text().strip(),
            "default_expense_account": self.default_expense_edit.text().strip(),
        }
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        try:
            if self.api_key_edit.text():
                keyring.set_password(SERVICE_NAME, "api_key", self.api_key_edit.text())
            if username and self.password_edit.text():
                keyring.set_password(SERVICE_NAME, username, self.password_edit.text())
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

    @property
    def api_key(self) -> str:
        return self.api_key_edit.text().strip()

    @property
    def db_name(self) -> str:
        return self.db_name_edit.text().strip()

    @property
    def server(self) -> str:
        return self.server_edit.text().strip() or "lb1.wizcloud.co.il"

    @property
    def vat_account(self) -> str:
        return self.vat_account_edit.text().strip()

    @property
    def default_expense_account(self) -> str:
        return self.default_expense_edit.text().strip()


def _browse_folder(line_edit: QLineEdit):
    folder = QFileDialog.getExistingDirectory(None, "בחר תיקייה")
    if folder:
        line_edit.setText(folder)
