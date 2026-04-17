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

from core.hashavshevet import HashavshevetClient
from core.pdf_processor import PDFProcessor
from core.reporter import Reporter
from core.supplier_manager import SupplierManager
from models.document import DocumentRecord
from models.supplier import Supplier


class RunWorker(QThread):
    log_signal       = pyqtSignal(str)
    progress_signal  = pyqtSignal(int, int)
    unknown_supplier = pyqtSignal(str, str)   # snippet, filename
    finished_signal  = pyqtSignal(list, str, str)
    error_signal     = pyqtSignal(str)

    def __init__(
        self,
        invoice_folder: str,
        receipt_folder: str,
        api_key: str,
        db_name: str,
        web_username: str,
        web_password: str,
        vat_account: str,
        default_expense_account: str,
        supplier_manager: SupplierManager,
        demo_mode: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.invoice_folder          = invoice_folder
        self.receipt_folder          = receipt_folder
        self.api_key                 = api_key
        self.db_name                 = db_name
        self.web_username            = web_username
        self.web_password            = web_password
        self.vat_account             = vat_account
        self.default_expense_account = default_expense_account
        self.supplier_manager        = supplier_manager
        self.demo_mode               = demo_mode
        self._stop_requested         = False

        self._pending_supplier: Optional[Supplier] = None
        self._supplier_ready   = asyncio.Event()

    # ── Qt entry point ────────────────────────────────────────────────────────

    def run(self):
        asyncio.run(self._run_async())

    def stop(self):
        self._stop_requested = True

    def resolve_supplier(self, supplier: Optional[Supplier]):
        self._pending_supplier = supplier
        asyncio.get_event_loop().call_soon_threadsafe(self._supplier_ready.set)

    # ── Async core ────────────────────────────────────────────────────────────

    async def _run_async(self):
        processor = PDFProcessor()
        reporter  = Reporter()
        client: Optional[HashavshevetClient] = None

        try:
            invoices  = sorted(glob.glob(os.path.join(self.invoice_folder, "*.pdf")))
            receipts  = sorted(glob.glob(os.path.join(self.receipt_folder, "*.pdf")))
            all_files = [(p, "חשבונית") for p in invoices] + \
                        [(p, "קבלה")    for p in receipts]
            total = len(all_files)

            self.log_signal.emit(
                f"נמצאו {len(invoices)} חשבוניות ו-{len(receipts)} קבלות ({total} סה\"כ)"
            )

            if total == 0:
                self.log_signal.emit("אין קבצים לעיבוד.")
                self.finished_signal.emit([], "", "")
                return

            if not self.demo_mode:
                client = HashavshevetClient(
                    api_key=self.api_key,
                    db_name=self.db_name,
                    web_username=self.web_username,
                    web_password=self.web_password,
                    vat_account=self.vat_account,
                    log=lambda msg: self.log_signal.emit(msg),
                )
                await client.start()
                await client.api_login()
                await client.web_login()

            records: List[DocumentRecord] = []
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")

            for idx, (pdf_path, doc_type) in enumerate(all_files, 1):
                if self._stop_requested:
                    self.log_signal.emit("הרצה הופסקה.")
                    break

                self.progress_signal.emit(idx, total)
                fname  = os.path.basename(pdf_path)
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
                        snippet = data["text"][:300].replace("\n", " ")
                        self._supplier_ready.clear()
                        self.unknown_supplier.emit(snippet, fname)
                        await self._supplier_ready.wait()
                        supplier = self._pending_supplier

                    if supplier is None:
                        rec.supplier = "לא זוהה"
                        rec.action   = "דולג"
                        self.log_signal.emit("  → דולג (ספק לא זוהה)")
                        records.append(rec)
                        continue

                    rec.supplier = supplier.name

                    if not supplier.should_upload:
                        rec.action = "דולג"
                        self.log_signal.emit("  → דולג (הגדרת ספק: לא להעלות)")
                        records.append(rec)
                        continue

                    # Resolve account codes (supplier-specific or global default)
                    supplier_account = supplier.account_key or supplier.name
                    expense_account  = supplier.expense_account or self.default_expense_account

                    # VAT
                    if doc_type == "חשבונית":
                        vat_rate       = supplier.vat_rate
                        vat_amount     = round(rec.total_amount * vat_rate / (100 + vat_rate), 2)
                        rec.vat_amount = vat_amount
                        rec.vat_rate   = vat_rate
                    else:
                        rec.vat_amount = 0.0
                        rec.vat_rate   = 0.0

                    # Upload
                    if self.demo_mode:
                        rec.action = "הועלה (מצב בדיקה)"
                        self.log_signal.emit("  → [מצב בדיקה] הועלה ✔")
                    else:
                        if doc_type == "חשבונית":
                            ok = await client.upload_invoice(
                                supplier_name=supplier.name,
                                supplier_account=supplier_account,
                                expense_account=expense_account,
                                doc_number=rec.doc_number,
                                date=rec.date,
                                total_amount=rec.total_amount,
                                vat_amount=rec.vat_amount,
                                pdf_path=pdf_path,
                            )
                        else:
                            ok = await client.upload_receipt(
                                supplier_name=supplier.name,
                                supplier_account=supplier_account,
                                expense_account=expense_account,
                                doc_number=rec.doc_number,
                                date=rec.date,
                                total_amount=rec.total_amount,
                                pdf_path=pdf_path,
                            )
                        rec.action = "הועלה" if ok else "שגיאה"
                        self.log_signal.emit(f"  → {'הועלה ✔' if ok else 'שגיאה ✘'}")

                except Exception as exc:
                    rec.action    = "שגיאה"
                    rec.error_msg = str(exc)
                    self.log_signal.emit(f"  → שגיאה: {exc}")

                records.append(rec)

            if client:
                await client.web_logout()

            self.log_signal.emit("מייצר דוחות…")
            word_path  = reporter.generate_word(records, timestamp)
            excel_path = reporter.generate_excel(records, timestamp)
            self.log_signal.emit(f"דוח Word:  {word_path}")
            self.log_signal.emit(f"דוח Excel: {excel_path}")
            self.log_signal.emit("✔ הרצה הסתיימה.")
            self.finished_signal.emit(records, word_path, excel_path)

        except Exception as exc:
            self.error_signal.emit(str(exc))
        finally:
            if client:
                await client.close()
