import os

import pdfplumber
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QPushButton,
    QFileDialog, QMessageBox, QHeaderView,
)

from core.supplier_manager import SupplierManager
from gui.supplier_dialog import SupplierDialog
from models.supplier import Supplier


class SuppliersTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.manager = SupplierManager()
        self._build_ui()
        self._refresh_table()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)

        title = QLabel("ניהול ספקים")
        title.setObjectName("section_title")
        layout.addWidget(title)

        # Toolbar
        toolbar = QHBoxLayout()
        add_btn    = QPushButton("+ הוסף ספק")
        add_btn.setObjectName("btn_success")
        edit_btn   = QPushButton("עריכה")
        del_btn    = QPushButton("מחיקה")
        del_btn.setObjectName("btn_danger")
        import_btn = QPushButton("ייבא מ-PDF")
        import_btn.setObjectName("btn_secondary")
        fix_btn    = QPushButton("תקן כיוון עברית")
        fix_btn.setObjectName("btn_secondary")
        fix_btn.setToolTip("תקן שמות ספקים שיובאו הפוכים מקובץ PDF ישן")

        add_btn.clicked.connect(self._add_supplier)
        edit_btn.clicked.connect(self._edit_supplier)
        del_btn.clicked.connect(self._delete_supplier)
        import_btn.clicked.connect(self._import_from_pdf)
        fix_btn.clicked.connect(self._fix_hebrew_direction)

        for btn in (add_btn, edit_btn, del_btn, import_btn, fix_btn):
            toolbar.addWidget(btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["שם ספק", "כינויים", "להעלות?", 'מע"מ %', "הערות"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._edit_supplier)
        layout.addWidget(self.table)

        count_label = QLabel("")
        count_label.setObjectName("count_label")
        layout.addWidget(count_label)
        self._count_label = count_label

    # ── Table helpers ─────────────────────────────────────────────────────────

    def _refresh_table(self):
        self.table.setRowCount(0)
        for supplier in self.manager.suppliers:
            row = self.table.rowCount()
            self.table.insertRow(row)
            items = [
                supplier.name,
                ", ".join(supplier.aliases),
                "כן" if supplier.should_upload else "לא",
                f"{supplier.vat_rate}%",
                supplier.notes,
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, supplier.id)
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, col, item)
        self._count_label.setText(f"סה\"כ ספקים: {self.table.rowCount()}")

    def _selected_supplier(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        supplier_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        return self.manager.get_by_id(supplier_id)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _add_supplier(self):
        dlg = SupplierDialog(parent=self)
        if dlg.exec():
            self.manager.add(dlg.result_supplier)
            self._refresh_table()

    def _edit_supplier(self):
        supplier = self._selected_supplier()
        if not supplier:
            QMessageBox.information(self, "עריכה", "יש לבחור ספק בטבלה.")
            return
        dlg = SupplierDialog(supplier=supplier, parent=self)
        if dlg.exec():
            self.manager.update(dlg.result_supplier)
            self._refresh_table()

    def _delete_supplier(self):
        supplier = self._selected_supplier()
        if not supplier:
            QMessageBox.information(self, "מחיקה", "יש לבחור ספק בטבלה.")
            return
        reply = QMessageBox.question(
            self, "אישור מחיקה",
            f"למחוק את הספק \"{supplier.name}\"?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.manager.delete(supplier.id)
            self._refresh_table()

    def _fix_hebrew_direction(self):
        fixed = self.manager.fix_all_directions()
        self._refresh_table()
        if fixed:
            QMessageBox.information(self, "תיקון כיוון", f"תוקנו {fixed} שמות ספקים ✔")
        else:
            QMessageBox.information(self, "תיקון כיוון", "לא נמצאו שמות הפוכים לתיקון.")

    def _import_from_pdf(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "בחר קובץ PDF של רשימת ספקים", "", "PDF Files (*.pdf)"
        )
        if not path:
            return
        text = ""
        try:
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    text += (page.extract_text() or "") + "\n"
        except Exception as exc:
            QMessageBox.critical(self, "שגיאה", f"לא ניתן לקרוא את הקובץ:\n{exc}")
            return
        added = self.manager.import_from_text(text)
        self._refresh_table()
        QMessageBox.information(self, "ייבוא", f"נוספו {added} ספקים חדשים.")
