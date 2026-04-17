"""
WizCloud (חשבשבת) browser automation via Playwright.

NOTE: The SELECTORS dict below must be calibrated against the live
https://home.wizcloud.co.il/ interface on first use. All selectors
live here so they can be updated without touching the logic below.
"""

import asyncio
from typing import Callable, Optional

from playwright.async_api import async_playwright, Page, Browser, Playwright

WIZCLOUD_URL = "https://home.wizcloud.co.il/"

# ── Selectors ─────────────────────────────────────────────────────────────────
# Update these after inspecting the WizCloud interface with DevTools.
SELECTORS = {
    # Login page
    "username":         'input[name="user"], input[type="text"]',
    "password":         'input[name="password"], input[type="password"]',
    "login_btn":        'button[type="submit"], input[type="submit"], button:has-text("כניסה")',
    # Main nav / logout
    "logout_btn":       'a:has-text("יציאה"), button:has-text("יציאה"), [data-action="logout"]',
    # Supplier invoice — navigate to new entry
    "nav_supplier_inv": 'a:has-text("חשבונית ספק"), a:has-text("חשבוניות ספקים")',
    "btn_new_entry":    'button:has-text("חדש"), a:has-text("חדש"), [data-action="new"]',
    # Invoice / receipt form fields
    "field_supplier":   'input[name="supplier"], input[placeholder*="ספק"]',
    "field_doc_number": 'input[name="ivnum"], input[name="docnum"], input[placeholder*="מספר"]',
    "field_date":       'input[name="ivdate"], input[name="date"], input[type="date"]',
    "field_pretax":     'input[name="qprice"], input[name="amount"], input[placeholder*="לפני מע"]',
    "field_vat":        'input[name="vat"], input[placeholder*="מע"]',
    "field_total":      'input[name="totprice"], input[name="total"]',
    "file_input":       'input[type="file"]',
    "btn_save":         'button:has-text("שמור"), button:has-text("אישור"), button[type="submit"]',
}


class HashavshevetAutomation:
    def __init__(self, username: str, password: str, log: Callable[[str], None] = print):
        self.username = username
        self.password = password
        self.log = log
        self._pw: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self, headless: bool = False):
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=headless, slow_mo=150)
        self._page = await self._browser.new_page()
        self._page.set_default_timeout(20_000)

    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    # ── Auth ──────────────────────────────────────────────────────────────────

    async def login(self):
        self.log("מתחבר לחשבשבת…")
        await self._page.goto(WIZCLOUD_URL)
        await self._page.wait_for_load_state("networkidle")
        await self._page.fill(SELECTORS["username"], self.username)
        await self._page.fill(SELECTORS["password"], self.password)
        await self._page.click(SELECTORS["login_btn"])
        await self._page.wait_for_load_state("networkidle")
        self.log("התחברות הצליחה ✔")

    async def logout(self):
        self.log("מתנתק מהמערכת…")
        try:
            await self._page.click(SELECTORS["logout_btn"])
            await self._page.wait_for_load_state("networkidle")
            self.log("יצאת מהמערכת ✔")
        except Exception as exc:
            self.log(f"אזהרה: לא הצלחתי לצאת — {exc}")

    # ── Upload ────────────────────────────────────────────────────────────────

    async def upload_invoice(
        self,
        supplier_name: str,
        doc_number: str,
        date: str,
        total_amount: float,
        vat_amount: float,
        pdf_path: str,
    ) -> bool:
        pretax = round(total_amount - vat_amount, 2)
        try:
            await self._navigate_to_new_entry()
            await self._fill_common_fields(supplier_name, doc_number, date)
            await self._try_fill(SELECTORS["field_pretax"], str(pretax))
            await self._try_fill(SELECTORS["field_vat"],    str(vat_amount))
            await self._try_fill(SELECTORS["field_total"],  str(total_amount))
            await self._attach_file(pdf_path)
            await self._page.click(SELECTORS["btn_save"])
            await self._page.wait_for_load_state("networkidle")
            return True
        except Exception as exc:
            self.log(f"שגיאה בהעלאת חשבונית {doc_number}: {exc}")
            return False

    async def upload_receipt(
        self,
        supplier_name: str,
        doc_number: str,
        date: str,
        total_amount: float,
        pdf_path: str,
    ) -> bool:
        try:
            await self._navigate_to_new_entry()
            await self._fill_common_fields(supplier_name, doc_number, date)
            await self._try_fill(SELECTORS["field_total"], str(total_amount))
            await self._attach_file(pdf_path)
            await self._page.click(SELECTORS["btn_save"])
            await self._page.wait_for_load_state("networkidle")
            return True
        except Exception as exc:
            self.log(f"שגיאה בהעלאת קבלה {doc_number}: {exc}")
            return False

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _navigate_to_new_entry(self):
        await self._page.click(SELECTORS["nav_supplier_inv"])
        await self._page.wait_for_load_state("networkidle")
        await self._page.click(SELECTORS["btn_new_entry"])
        await self._page.wait_for_load_state("networkidle")

    async def _fill_common_fields(self, supplier: str, doc_number: str, date: str):
        await self._try_fill(SELECTORS["field_supplier"],   supplier)
        await self._try_fill(SELECTORS["field_doc_number"], doc_number)
        await self._try_fill(SELECTORS["field_date"],       date)

    async def _try_fill(self, selector: str, value: str):
        """Fill the first matching selector; silently skip if not found."""
        try:
            await self._page.fill(selector, value)
        except Exception:
            pass

    async def _attach_file(self, pdf_path: str):
        try:
            await self._page.set_input_files(SELECTORS["file_input"], pdf_path)
        except Exception as exc:
            self.log(f"אזהרה: לא הצלחתי לצרף קובץ — {exc}")
