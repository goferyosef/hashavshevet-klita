from datetime import datetime

from PyQt6.QtCore import Qt, QMetaObject, Q_ARG, pyqtSlot
from PyQt6.QtGui import QTextCursor, QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QProgressBar, QCheckBox, QMessageBox,
)

from core.runner import RunWorker
from gui.supplier_dialog import UnknownSupplierDialog


class RunTab(QWidget):
    def __init__(self, config_tab, suppliers_tab, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.config_tab    = config_tab
        self.suppliers_tab = suppliers_tab
        self._worker       = None
        self._build_ui()

        # Signal connected lazily when worker created
        self._word_path  = ""
        self._excel_path = ""

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(12)

        title = QLabel("הרצת עיבוד")
        title.setObjectName("section_title")
        layout.addWidget(title)

        # Controls row
        ctrl = QHBoxLayout()
        self.start_btn = QPushButton("▶  התחל עיבוד")
        self.start_btn.setObjectName("btn_success")
        self.start_btn.setFixedHeight(38)
        self.start_btn.clicked.connect(self._start)

        self.stop_btn = QPushButton("■  עצור")
        self.stop_btn.setObjectName("btn_danger")
        self.stop_btn.setFixedHeight(38)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop)

        self.demo_check = QCheckBox("מצב בדיקה (ללא העלאה לחשבשבת)")
        self.demo_check.setChecked(False)

        ctrl.addWidget(self.start_btn)
        ctrl.addWidget(self.stop_btn)
        ctrl.addSpacing(20)
        ctrl.addWidget(self.demo_check)
        ctrl.addStretch()
        layout.addLayout(ctrl)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        # Log
        layout.addWidget(QLabel("יומן פעולות:"))
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(self.log_view)

        # Open reports row
        report_row = QHBoxLayout()
        self.open_word_btn  = QPushButton("פתח דוח Word")
        self.open_excel_btn = QPushButton("פתח דוח Excel")
        self.open_word_btn.setEnabled(False)
        self.open_excel_btn.setEnabled(False)
        self.open_word_btn.clicked.connect(self._open_word)
        self.open_excel_btn.clicked.connect(self._open_excel)
        report_row.addStretch()
        report_row.addWidget(self.open_word_btn)
        report_row.addWidget(self.open_excel_btn)
        layout.addLayout(report_row)

    # ── Run control ───────────────────────────────────────────────────────────

    def _start(self):
        cfg = self.config_tab
        if not cfg.invoice_folder or not cfg.receipt_folder:
            QMessageBox.warning(self, "הגדרות חסרות", "יש להגדיר תיקיות קלט בלשונית 'הגדרות'.")
            return
        if not self.demo_check.isChecked() and (not cfg.api_key or not cfg.db_name):
            QMessageBox.warning(self, "הגדרות חסרות", "יש להזין API Key ו-DB Name בלשונית 'הגדרות'.")
            return

        self.log_view.clear()
        self.progress.setValue(0)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.open_word_btn.setEnabled(False)
        self.open_excel_btn.setEnabled(False)
        self._append_log(f"▶ הרצה החלה — {datetime.now().strftime('%H:%M:%S')}")

        sm = self.suppliers_tab.manager
        self._worker = RunWorker(
            invoice_folder=cfg.invoice_folder,
            receipt_folder=cfg.receipt_folder,
            api_key=cfg.api_key,
            db_name=cfg.db_name,
            server=cfg.server,
            web_username=cfg.username,
            web_password=cfg.password,
            vat_account=cfg.vat_account,
            default_expense_account=cfg.default_expense_account,
            supplier_manager=sm,
            demo_mode=self.demo_check.isChecked(),
        )
        self._worker.log_signal.connect(self._append_log)
        self._worker.progress_signal.connect(self._update_progress)
        self._worker.unknown_supplier.connect(self._handle_unknown_supplier)
        self._worker.finished_signal.connect(self._on_finished)
        self._worker.error_signal.connect(self._on_error)
        self._worker.start()

    def _stop(self):
        if self._worker:
            self._worker.stop()
        self.stop_btn.setEnabled(False)

    # ── Slots ─────────────────────────────────────────────────────────────────

    @pyqtSlot(str)
    def _append_log(self, msg: str):
        self.log_view.append(msg)
        self.log_view.moveCursor(QTextCursor.MoveOperation.End)

    @pyqtSlot(int, int)
    def _update_progress(self, current: int, total: int):
        self.progress.setMaximum(total)
        self.progress.setValue(current)
        self.progress.setFormat(f"{current} / {total}")

    @pyqtSlot(str, str)
    def _handle_unknown_supplier(self, snippet: str, fname: str):
        """Show dialog to identify an unknown supplier, then resume the worker."""
        dlg = UnknownSupplierDialog(
            snippet, fname, self.suppliers_tab.manager.suppliers, parent=self
        )
        if dlg.exec():
            supplier = dlg.chosen_supplier
            if supplier and supplier.id not in {s.id for s in self.suppliers_tab.manager.suppliers}:
                self.suppliers_tab.manager.add(supplier)
                self.suppliers_tab._refresh_table()
            self._worker.resolve_supplier(supplier)
        else:
            self._worker.resolve_supplier(None)   # skip this document

    @pyqtSlot(list, str, str)
    def _on_finished(self, records, word_path, excel_path):
        self._word_path  = word_path
        self._excel_path = excel_path
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress.setValue(self.progress.maximum())
        if word_path:
            self.open_word_btn.setEnabled(True)
        if excel_path:
            self.open_excel_btn.setEnabled(True)
        # Notify reports tab
        self.window().findChild(object, "reports_tab_widget")
        try:
            self.window().reports_tab.update_paths(word_path, excel_path)
        except AttributeError:
            pass

    @pyqtSlot(str)
    def _on_error(self, msg: str):
        self._append_log(f"✘ שגיאה קריטית: {msg}")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        QMessageBox.critical(self, "שגיאה", msg)

    # ── Open reports ──────────────────────────────────────────────────────────

    def _open_word(self):
        if self._word_path:
            import os
            os.startfile(self._word_path)

    def _open_excel(self):
        if self._excel_path:
            import os
            os.startfile(self._excel_path)
