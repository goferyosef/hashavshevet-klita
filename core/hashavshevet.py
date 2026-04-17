"""
WizCloud (חשבשבת) hybrid integration:
  - REST API  → create journal entries (invoices / receipts)
  - Playwright → attach PDF file to the created entry
"""

import asyncio
from typing import Callable, Optional

import httpx
from playwright.async_api import async_playwright, Page, Browser, Playwright

WEB_URL = "https://home.wizcloud.co.il/"

# ── Playwright selectors for the web UI (file attachment only) ────────────────
# Update these after inspecting the WizCloud interface with DevTools.
WEB_SELECTORS = {
    "username":        'input[name="user"], input[type="text"]:first-of-type',
    "password":        'input[type="password"]',
    "login_btn":       'button[type="submit"], input[type="submit"], button:has-text("כניסה")',
    "logout_btn":      'a:has-text("יציאה"), button:has-text("יציאה"), [data-action="logout"]',
    # Navigate to an existing journal entry by its batch/ref number
    "search_input":    'input[placeholder*="חיפוש"], input[name="search"]',
    # File input on the entry form
    "file_input":      'input[type="file"]',
    "btn_save":        'button:has-text("שמור"), button:has-text("אישור")',
}


class HashavshevetClient:
    def __init__(
        self,
        api_key: str,
        db_name: str,
        server: str,
        web_username: str,
        web_password: str,
        vat_account: str,
        log: Callable[[str], None] = print,
    ):
        self.api_key      = api_key
        self.db_name      = db_name
        self.server       = server.rstrip("/")
        self.web_username = web_username
        self.web_password = web_password
        self.vat_account  = vat_account
        self.log          = log

        self._token: Optional[str] = None
        self._http: Optional[httpx.AsyncClient] = None

        self._pw:      Optional[Playwright] = None
        self._browser: Optional[Browser]    = None
        self._page:    Optional[Page]       = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self):
        base = f"https://{self.server}" if not self.server.startswith("http") else self.server
        self._http = httpx.AsyncClient(base_url=base, timeout=30)

    async def close(self):
        if self._http:
            await self._http.aclose()
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    # ── API Auth ──────────────────────────────────────────────────────────────

    async def api_login(self) -> bool:
        self.log("מתחבר ל-API של חשבשבת…")
        resp = await self._http.get(
            f"/createSession/{self.api_key}/{self.db_name}"
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data.get("wizAuthToken") or data.get("token") or data.get("Token")
        if not self._token:
            raise RuntimeError(f"לא התקבל טוקן. תשובת שרת: {data}")
        # Docs show raw token in Authorization (not Bearer prefix)
        self._http.headers.update({"Authorization": self._token})
        self.log("התחברות API הצליחה ✔")
        return True

    # ── Web (Playwright) Auth — used only for file attachment ─────────────────

    async def web_login(self):
        self.log("פותח דפדפן לצירוף קבצים…")
        self._pw      = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=False, slow_mo=150)
        self._page    = await self._browser.new_page()
        self._page.set_default_timeout(20_000)
        await self._page.goto(WEB_URL)
        await self._page.wait_for_load_state("networkidle")
        await self._page.fill(WEB_SELECTORS["username"], self.web_username)
        await self._page.fill(WEB_SELECTORS["password"], self.web_password)
        await self._page.click(WEB_SELECTORS["login_btn"])
        await self._page.wait_for_load_state("networkidle")
        self.log("התחברות דפדפן הצליחה ✔")

    async def web_logout(self):
        if not self._page:
            return
        try:
            await self._page.click(WEB_SELECTORS["logout_btn"])
            await self._page.wait_for_load_state("networkidle")
            self.log("יצאת מהדפדפן ✔")
        except Exception as exc:
            self.log(f"אזהרה: יציאה מהדפדפן נכשלה — {exc}")

    # ── Upload Invoice (חשבונית) ───────────────────────────────────────────────

    async def upload_invoice(
        self,
        supplier_name: str,
        supplier_account: str,
        expense_account: str,
        doc_number: str,
        date: str,
        total_amount: float,
        vat_amount: float,
        pdf_path: str,
    ) -> bool:
        net_amount = round(total_amount - vat_amount, 2)

        # Step 1 — open new batch
        batch_no = await self._new_batch()
        if batch_no is None:
            return False

        # Step 2 — post journal row
        ref = int(doc_number) if doc_number.isdigit() else 0
        payload = {
            "insertolastb": True,
            "batchNo": batch_no,
            "check": True,
            "issue": True,
            "rows": [
                {
                    "TransDebID":   expense_account,
                    "TransCredID":  supplier_account,
                    "Description":  f"חשבונית {supplier_name}",
                    "Referance":    ref,
                    "ValueDate":    date,
                    "SuF":          total_amount,
                    "Details":      f"חשבונית {doc_number}",
                    "moves": [
                        {"AccountKey": expense_account,  "DebitCredit": 1, "Suf": net_amount},
                        {"AccountKey": self.vat_account, "DebitCredit": 1, "Suf": vat_amount},
                        {"AccountKey": supplier_account, "DebitCredit": 0, "Suf": total_amount},
                    ],
                }
            ],
        }
        ok = await self._post_json("/jtransApi/tmpBatch", payload)
        if not ok:
            return False

        # Step 3 — attach PDF via browser
        if pdf_path and self._page:
            await self._attach_file(doc_number, pdf_path)

        return True

    # ── Upload Receipt (קבלה) ─────────────────────────────────────────────────

    async def upload_receipt(
        self,
        supplier_name: str,
        supplier_account: str,
        expense_account: str,
        doc_number: str,
        date: str,
        total_amount: float,
        pdf_path: str,
    ) -> bool:
        # Receipts: no VAT — single debit/credit journal entry
        batch_no = await self._new_batch()
        if batch_no is None:
            return False

        ref = int(doc_number) if doc_number.isdigit() else 0
        payload = {
            "insertolastb": True,
            "batchNo": batch_no,
            "check": True,
            "issue": True,
            "rows": [
                {
                    "TransDebID":  expense_account,
                    "TransCredID": supplier_account,
                    "Description": f"קבלה {supplier_name}",
                    "Referance":   ref,
                    "ValueDate":   date,
                    "SuF":         total_amount,
                    "Details":     f"קבלה {doc_number}",
                    "moves": [
                        {"AccountKey": expense_account,  "DebitCredit": 1, "Suf": total_amount},
                        {"AccountKey": supplier_account, "DebitCredit": 0, "Suf": total_amount},
                    ],
                }
            ],
        }
        ok = await self._post_json("/jtransApi/tmpBatch", payload)
        if not ok:
            return False

        if pdf_path and self._page:
            await self._attach_file(doc_number, pdf_path)

        return True

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _new_batch(self) -> Optional[int]:
        try:
            resp = await self._http.post("/jtransApi/newBatch")
            resp.raise_for_status()
            data = resp.json()
            # API returns lowercase "batchno" per docs
            batch_no = data.get("batchno") or data.get("batchNo") or data.get("BatchNo")
            return int(batch_no)
        except Exception as exc:
            self.log(f"שגיאה ביצירת batch: {exc}")
            return None

    async def _post_json(self, path: str, payload: dict) -> bool:
        try:
            resp = await self._http.post(path, json=payload)
            resp.raise_for_status()
            return True
        except Exception as exc:
            self.log(f"שגיאת API ({path}): {exc}")
            return False

    async def _attach_file(self, doc_number: str, pdf_path: str):
        """Navigate to the entry in the web UI and attach the PDF."""
        try:
            # Try to search/navigate to the document
            try:
                await self._page.fill(WEB_SELECTORS["search_input"], doc_number)
                await self._page.keyboard.press("Enter")
                await self._page.wait_for_load_state("networkidle")
            except Exception:
                pass  # Search field may not be easily accessible — attachment skipped

            await self._page.set_input_files(WEB_SELECTORS["file_input"], pdf_path)
            await self._page.click(WEB_SELECTORS["btn_save"])
            await self._page.wait_for_load_state("networkidle")
            self.log(f"  קובץ צורף: {pdf_path}")
        except Exception as exc:
            self.log(f"  אזהרה: צירוף קובץ נכשל — {exc}")
