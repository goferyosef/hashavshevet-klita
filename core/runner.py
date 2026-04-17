"""
Main run orchestrator. Runs inside a QThread via asyncio.run().
Emits Qt signals for log messages, progress, and completion.
"""

import asyncio
import glob
import os
from datetime import datetime
from typing import List, Optional

from PyQt6.QtCore import QThread, pyqtSignal

from core.hashavshevet import HashavshevetAutomation
from core.pdf_processor import PDFProcessor
from core.reporter import Reporter
from core.supplier_manager import SupplierManager
from models.document import DocumentRecord
from models.supplier import Supplier


class RunWorker(QThread):
    log_signal       = pyqtSignal(str)          # log line
    progress_signal  = pyqtSignal(int, int)     # current, total
    # Emitted when an unknown supplier is found: (snippet, pdf_path)
    # GUI shows dialog, calls resolve_supplier() to continue.
    unknown_supplier = pyqtSignal(str, str)
    finished_signal  = pyqtSignal(list, str, str)  # records, word_path, excel_path
    error_signal     = pyqtSignal(str)

    def __init__(
        self,
        invoice_folder: str,
        receipt_folder: str,
        username: str,
        password: str,
        supplier_manager: SupplierManager,
        demo_mode: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.invoice_folder   = invoice_folder
        self.receipt_folder   = receipt_folder
        self.username         = username
        self.password         = password
        self.supplier_manager = supplier_manager
        self.demo_mode        = demo_mode
        self._stop_requested  = False

        # Used to hand back an identified supplier from the GUI thread
        self._pending_supplier: Optional[Supplier] = None
        self._supplier_ready   = asyncio.Event()

    # ── Qt entry point ────────────────────────────────────────────────────────

    def run(self):
        asyncio.run(self._run_async())

    def stop(self):
        self._stop_requested = True

    def resolve_supplier(self, supplier: Optional[Supplier]):
        """Called from GUI thread after user identifies an unknown supplier."""
        self._pending_supplier = supplier
        # Schedule set() on the loop running in this thread
        asyncio.get_event_loop().call_soon_threadsafe(self._supplier_ready.set)

    # ── Async core ────────────────────────────────────────────────────────────

    async def _run_async(self):
        processor  = PDFProcessor()
        reporter   = Reporter()
        automation: Optional[HashavshevetAutomation] = None

        try:
            # Collect all PDFs
            invoices = sorted(glob.glob(os.path.join(self.invoice_folder, "*.pdf")))
            receipts = sorted(glob.glob(os.path.join(self.receipt_folder, "*.pdf")))
            all_files = [(p, "חשבונית") for p in invoices] + \
                        [(p, "קבלה")    for p in receipts]

            total = len(all_files)
            self.log_signal.emit(f"נמצאו {len(invoices)} חשבוניות ו-{len(receipts)} קבלות ({total} סה\"כ)")

            if total == 0:
                self.log_signal.emit("אין קבצים לעיבוד.")
                self.finished_signal.emit([], "", "")
                return

            # Login
            if not self.demo_mode:
                automation = HashavshevetAutomation(
                    self.username, self.password,
                    log=lambda msg: self.log_signal.emit(msg),
                )
                await automation.start()
                await automation.login()

            records: List[DocumentRecord] = []
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")

            for idx, (pdf_path, doc_type) in enumerate(all_files, 1):
                if self._stop_requested:
                    self.log_signal.emit("הרצה הופסקה על ידי המשתמש.")
                    break

                self.progress_signal.emit(idx, total)
                fname = os.path.basename(pdf_path)
                folder = os.path.basename(os.path.dirname(pdf_path))
                self.log_signal.emit(f"[{idx}/{total}] מעבד: {fname}")

                rec = DocumentRecord(
                    file_name=fname,
                    folder=folder,
                    doc_type=doc_type,
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )

                try:
                    data = processor.extract(pdf_path)
                    rec.date         = data["date"]
                    rec.total_amount = data["total_amount"]
                    rec.doc_number   = data["doc_number"]

                    # Identify supplier
                    supplier = self.supplier_manager.find_best_match(data["text"])

                    if supplier is None:
                        # Ask the GUI
                        snippet = data["text"][:300].replace("\n", " ")
                        self._supplier_ready.clear()
                        self.unknown_supplier.emit(snippet, fname)
                        await self._supplier_ready.wait()
                        supplier = self._pending_supplier

                    if supplier is None:
                        rec.supplier = "לא זוהה"
                        rec.action   = "דולג"
                        self.log_signal.emit(f"  → דולג (ספק לא זוהה)")
                        records.append(rec)
                        continue

                    rec.supplier = supplier.name

                    if not supplier.should_upload:
                        rec.action = "דולג"
                        self.log_signal.emit(f"  → דולג (הגדרת ספק: לא להעלות)")
                        records.append(rec)
                        continue

                    # Calculate VAT
                    if doc_type == "חשבונית":
                        vat_rate      = supplier.vat_rate
                        # total_amount is the gross amount (inc. VAT)
                        vat_amount    = round(rec.total_amount * vat_rate / (100 + vat_rate), 2)
                        rec.vat_amount = vat_amount
                        rec.vat_rate   = vat_rate
                    else:
                        rec.vat_amount = 0.0
                        rec.vat_rate   = 0.0

                    # Upload
                    if self.demo_mode:
                        rec.action = "הועלה (מצב בדיקה)"
                        self.log_signal.emit(f"  → [מצב בדיקה] הועלה ✔")
                    else:
                        if doc_type == "חשבונית":
                            ok = await automation.upload_invoice(
                                supplier.name, rec.doc_number, rec.date,
                                rec.total_amount, rec.vat_amount, pdf_path,
                            )
                        else:
                            ok = await automation.upload_receipt(
                                supplier.name, rec.doc_number, rec.date,
                                rec.total_amount, pdf_path,
                            )
                        rec.action = "הועלה" if ok else "שגיאה"
                        self.log_signal.emit(f"  → {'הועלה ✔' if ok else 'שגיאה ✘'}")

                except Exception as exc:
                    rec.action    = "שגיאה"
                    rec.error_msg = str(exc)
                    self.log_signal.emit(f"  → שגיאה: {exc}")

                records.append(rec)

            # Logout
            if automation and not self._stop_requested:
                await automation.logout()

            # Reports
            self.log_signal.emit("מייצר דוחות…")
            word_path  = reporter.generate_word(records, timestamp)
            excel_path = reporter.generate_excel(records, timestamp)
            self.log_signal.emit(f"דוח Word: {word_path}")
            self.log_signal.emit(f"דוח Excel: {excel_path}")
            self.log_signal.emit("✔ הרצה הסתיימה.")
            self.finished_signal.emit(records, word_path, excel_path)

        except Exception as exc:
            self.error_signal.emit(str(exc))
        finally:
            if automation:
                await automation.close()
