import re
import os
from typing import Optional

import pdfplumber


# ── Regex patterns for Hebrew invoices / receipts ────────────────────────────

_DATE_PATTERNS = [
    r"\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b",
    r"\b\d{4}-\d{2}-\d{2}\b",
]

_AMOUNT_PATTERNS = [
    r'סה["\u05f4]כ\s+לתשלום[:\s]+[\u20aa]?\s*([\d,]+\.?\d*)',
    r'סה["\u05f4]כ\s+כולל\s+מע["\u05f4]מ[:\s]+[\u20aa]?\s*([\d,]+\.?\d*)',
    r'סה["\u05f4]כ[:\s]+[\u20aa]?\s*([\d,]+\.?\d*)',
    r'סכום\s+כולל[:\s]+[\u20aa]?\s*([\d,]+\.?\d*)',
    r'לתשלום[:\s]+[\u20aa]?\s*([\d,]+\.?\d*)',
    # Fallback: largest ₪ number in the document
    r'[\u20aa]\s*([\d,]+\.\d{2})',
]

_DOC_NUMBER_PATTERNS = [
    r'מס[\'׳\u05f3]?\s*חשבונית[:\s#]+(\w+)',
    r'חשבונית\s+מס[\'׳\u05f3]?\s*[:\s#]+(\w+)',
    r'מספר\s+חשבונית[:\s]+(\w+)',
    r'מס[\'׳\u05f3]?\s*קבלה[:\s#]+(\w+)',
    r'מספר\s+קבלה[:\s]+(\w+)',
    r'(?:invoice|receipt)\s*#?\s*:?\s*(\w+)',
    r'#\s*(\d{4,})',
]


class PDFProcessor:
    def extract(self, pdf_path: str) -> dict:
        """Return a dict with: text, date, total_amount, doc_number."""
        text = self._read_text(pdf_path)
        return {
            "text": text,
            "date": self._extract_date(text),
            "total_amount": self._extract_amount(text),
            "doc_number": self._extract_doc_number(text),
        }

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _read_text(pdf_path: str) -> str:
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    text += page_text + "\n"
        except Exception:
            pass
        return text

    @staticmethod
    def _extract_date(text: str) -> str:
        for pattern in _DATE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return ""

    @staticmethod
    def _extract_amount(text: str) -> float:
        all_matches = []
        for pattern in _AMOUNT_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    val = float(match.group(1).replace(",", ""))
                    all_matches.append(val)
                except (ValueError, IndexError):
                    continue
            if all_matches:
                # Return the largest value found by this (most-specific) pattern
                return max(all_matches)
        return 0.0

    @staticmethod
    def _extract_doc_number(text: str) -> str:
        for pattern in _DOC_NUMBER_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return ""
