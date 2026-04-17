import json
import os
from typing import List, Optional

from models.supplier import Supplier

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
SUPPLIERS_FILE = os.path.join(DATA_DIR, "suppliers.json")


class SupplierManager:
    def __init__(self):
        self.suppliers: List[Supplier] = []
        self.load()

    # ── Persistence ──────────────────────────────────────────────────────────

    def load(self):
        if os.path.exists(SUPPLIERS_FILE):
            with open(SUPPLIERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.suppliers = [Supplier.from_dict(s) for s in data]

    def save(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(SUPPLIERS_FILE, "w", encoding="utf-8") as f:
            json.dump([s.to_dict() for s in self.suppliers], f,
                      ensure_ascii=False, indent=2)

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def add(self, supplier: Supplier):
        self.suppliers.append(supplier)
        self.save()

    def update(self, supplier: Supplier):
        for i, s in enumerate(self.suppliers):
            if s.id == supplier.id:
                self.suppliers[i] = supplier
                break
        self.save()

    def delete(self, supplier_id: str):
        self.suppliers = [s for s in self.suppliers if s.id != supplier_id]
        self.save()

    def get_by_id(self, supplier_id: str) -> Optional[Supplier]:
        return next((s for s in self.suppliers if s.id == supplier_id), None)

    # ── Matching ─────────────────────────────────────────────────────────────

    def find_best_match(self, text: str, threshold: int = 75) -> Optional[Supplier]:
        """Fuzzy-match supplier name from extracted PDF text."""
        from rapidfuzz import fuzz

        best_score = 0
        best_supplier: Optional[Supplier] = None

        for supplier in self.suppliers:
            candidates = [supplier.name] + supplier.aliases
            for candidate in candidates:
                score = fuzz.partial_ratio(candidate.lower(), text.lower())
                if score > best_score:
                    best_score = score
                    best_supplier = supplier

        return best_supplier if best_score >= threshold else None

    # ── Bulk import from plain text (supplier-list PDF) ───────────────────────

    def import_from_text(self, text: str, fix_direction: bool = True) -> int:
        """
        Parse supplier entries from text.

        Handles two formats:
        1. חשבשבת account-list export rows:
           "[SORT] [ACCOUNT_KEY] [NAME] ^^^^^ [category] ([type]) [VAT_NUM]"
           → extracts name + account_key automatically.
        2. Plain lines: one supplier name per line.
        """
        from core.pdf_processor import _fix_line

        existing_names = {s.name.strip().lower() for s in self.suppliers}
        added = 0

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if fix_direction:
                line = _fix_line(line)

            name, account_key = _parse_hashavshevet_row(line)

            if not name or name.lower() in existing_names:
                continue

            self.add(Supplier(name=name, account_key=account_key))
            existing_names.add(name.lower())
            added += 1

        return added

    def fix_all_directions(self) -> int:
        """Reverse any supplier names that appear to be in visual (reversed) order."""
        from core.pdf_processor import _fix_line
        fixed = 0
        for supplier in self.suppliers:
            corrected = _fix_line(supplier.name)
            if corrected != supplier.name:
                supplier.name = corrected
                fixed += 1
        if fixed:
            self.save()
        return fixed


# ── חשבשבת account-list row parser ───────────────────────────────────────────

import re

# After direction-fix, rows look like:
#   "190 19011 שלהבת מפעל מזון ^^^^^ ספקים (ללא) 516793601"
#   SORT  KEY   NAME...          ^^^^^  CATEGORY  VAT
_HASHAV_ROW = re.compile(
    r'^\d+\s+'            # sort code
    r'(\d+)\s+'           # account key  (captured)
    r'(.+?)'              # supplier name (captured, non-greedy)
    r'\s+\^{3,}'          # ^^^^^ separator
)

# Hebrew characters range
_HEB_RE = re.compile(r'[\u05d0-\u05ea]')


def _parse_hashavshevet_row(line: str):
    """
    Try to parse a חשבשבת account-list row.
    Returns (name, account_key) or (None, '') if not a recognised format.
    """
    m = _HASHAV_ROW.match(line)
    if m:
        account_key = m.group(1)
        name        = m.group(2).strip()
        if _HEB_RE.search(name):
            return name, account_key

    # Fallback: if line has Hebrew text, use it as the name
    if _HEB_RE.search(line):
        # Strip leading/trailing numbers and punctuation
        name = re.sub(r'^[\d\s\(\)\.]+|[\d\s\(\)\.]+$', '', line).strip()
        if len(name) >= 2 and _HEB_RE.search(name):
            return name, ''

    return None, ''
