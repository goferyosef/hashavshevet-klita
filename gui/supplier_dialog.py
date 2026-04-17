"""
Two dialogs:
  1. SupplierDialog  — Add / Edit a supplier
  2. UnknownSupplierDialog — Identify an unrecognised supplier mid-run
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QDoubleSpinBox, QCheckBox,
    QPushButton, QComboBox, QTextEdit, QGroupBox, QMessageBox,
)

from models.supplier import Supplier


class SupplierDialog(QDialog):
    """Add or edit a supplier."""

    def __init__(self, supplier: Supplier = None, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setWindowTitle("עריכת ספק" if supplier else "הוספת ספק")
        self.setMinimumWidth(400)
        self._supplier = supplier
        self.result_supplier: Supplier = None
        self._build_ui()
        if supplier:
            self._populate(supplier)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        form = QFormLayout()
        form.setSpacing(10)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("שם הספק")
        form.addRow("שם:", self.name_edit)

        self.aliases_edit = QLineEdit()
        self.aliases_edit.setPlaceholderText("כינויים נוספים, מופרדים בפסיק")
        form.addRow("כינויים:", self.aliases_edit)

        self.upload_check = QCheckBox("העלה מסמכים מספק זה")
        self.upload_check.setChecked(True)
        form.addRow("", self.upload_check)

        self.vat_combo = QComboBox()
        self.vat_combo.addItem('18% (מלא)', 18.0)
        self.vat_combo.addItem('12% (⅔ מ-18%)', 12.0)
        form.addRow('שיעור מע"מ:', self.vat_combo)

        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText("הערות אופציונליות")
        form.addRow("הערות:", self.notes_edit)

        layout.addLayout(form)

        # Buttons
        btns = QHBoxLayout()
        ok_btn = QPushButton("אישור")
        ok_btn.setObjectName("btn_success")
        ok_btn.clicked.connect(self._accept)
        cancel_btn = QPushButton("ביטול")
        cancel_btn.setObjectName("btn_secondary")
        cancel_btn.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(ok_btn)
        layout.addLayout(btns)

    def _populate(self, s: Supplier):
        self.name_edit.setText(s.name)
        self.aliases_edit.setText(", ".join(s.aliases))
        self.upload_check.setChecked(s.should_upload)
        idx = self.vat_combo.findData(s.vat_rate)
        if idx >= 0:
            self.vat_combo.setCurrentIndex(idx)
        self.notes_edit.setText(s.notes)

    def _accept(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "שגיאה", "יש להזין שם ספק.")
            return
        aliases = [a.strip() for a in self.aliases_edit.text().split(",") if a.strip()]
        self.result_supplier = Supplier(
            id=self._supplier.id if self._supplier else Supplier.__dataclass_fields__["id"].default_factory(),
            name=name,
            should_upload=self.upload_check.isChecked(),
            vat_rate=self.vat_combo.currentData(),
            aliases=aliases,
            notes=self.notes_edit.text().strip(),
        )
        self.accept()


class UnknownSupplierDialog(QDialog):
    """
    Shown when a PDF's supplier could not be identified.
    User can assign an existing supplier, add a new one, or skip.
    """

    def __init__(self, text_snippet: str, file_name: str,
                 suppliers, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setWindowTitle("ספק לא זוהה")
        self.setMinimumWidth(500)
        self.suppliers = suppliers            # List[Supplier]
        self.chosen_supplier: Supplier = None  # None = skip
        self._build_ui(text_snippet, file_name)

    def _build_ui(self, snippet: str, fname: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(QLabel(f"<b>קובץ:</b> {fname}"))

        snippet_box = QTextEdit()
        snippet_box.setReadOnly(True)
        snippet_box.setPlainText(snippet)
        snippet_box.setFixedHeight(100)
        layout.addWidget(QLabel("תוכן מתוך המסמך:"))
        layout.addWidget(snippet_box)

        layout.addWidget(QLabel("בחר ספק:"))
        self.supplier_combo = QComboBox()
        self.supplier_combo.addItem("— הוסף ספק חדש —", None)
        for s in self.suppliers:
            self.supplier_combo.addItem(s.name, s)
        layout.addWidget(self.supplier_combo)

        btns = QHBoxLayout()
        ok_btn = QPushButton("אישור")
        ok_btn.setObjectName("btn_success")
        ok_btn.clicked.connect(self._accept)
        skip_btn = QPushButton("דלג על מסמך זה")
        skip_btn.setObjectName("btn_secondary")
        skip_btn.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(skip_btn)
        btns.addWidget(ok_btn)
        layout.addLayout(btns)

    def _accept(self):
        supplier = self.supplier_combo.currentData()
        if supplier is None:
            # "Add new" selected — open SupplierDialog
            dlg = SupplierDialog(parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.chosen_supplier = dlg.result_supplier
                self.accept()
        else:
            self.chosen_supplier = supplier
            self.accept()
