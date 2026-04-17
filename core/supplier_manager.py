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
    Returns (name, account_key) or (None, '') to skip this line.
    """
    # Skip obvious header / garbage lines
    if _is_garbage(line):
        return None, ''

    # Format 1: structured חשבשבת row — "[SORT] [KEY] [NAME] ^^^^^..."
    m = _HASHAV_ROW.match(line)
    if m:
        account_key = m.group(1)
        name        = m.group(2).strip()
        if _HEB_RE.search(name) and not _is_garbage(name):
            return name, account_key

    # Format 2: plain Hebrew line (no ^^^^^ marker)
    if '^' not in line and _HEB_RE.search(line):
        name = re.sub(r'^[\d\s\(\)\.\"]+|[\d\s\(\)\.\"]+$', '', line).strip()
        if len(name) >= 3 and _HEB_RE.search(name) and not _is_garbage(name):
            return name, ''

    return None, ''


# Words that appear in headers/footers but never in real supplier names
_HEADER_WORDS = {
    # Correct (logical) forms
    'קוד', 'מיון', 'מפתח', 'חשבון', 'החשבון', 'חתך', 'ראשי', 'מאזן',
    'אינדקס', 'דוח', 'חשבונות', 'תאריך', 'סידורי', 'ממוין',
    'מספר', 'תנועות', 'מתוך',
    # Reversed (visual-order) forms of the same words
    'דוק', 'ןוימ', 'חתפמ', 'ןובשח', 'ןובשחה', 'ךתח', 'ישאר', 'ןזאמ',
    'סקדניא', 'חוד', 'תונובשח', 'ךיראת', 'ירודיס', 'ןיוממ',
    'רפסמ', 'תועונת', 'ךותמ',
}
# Single words that are alone sufficient to identify a garbage line
_HEADER_SINGLES = {'עמוד', 'דומע'}


def _is_garbage(text: str) -> bool:
    """Return True if text is a header row, timestamp, or otherwise not a supplier name."""
    from core.pdf_processor import _fix_line
    t = text.strip()

    # Timestamp / date — both normal and reversed form (e.g. 6202/4/71)
    if re.search(r'\d{1,2}/\d{1,2}/\d{2,4}', t) or re.search(r'\d{4}/\d{1,2}', t):
        return True
    # Contains ^^^^^ but not in structured format (partial / broken)
    if '^^^^' in t and not _HASHAV_ROW.match(t):
        return True
    # Very short after stripping punctuation
    clean = re.sub(r'[\s\"\'\.\-]', '', t)
    if len(clean) <= 3:
        return True
    # Check header keywords in both original and direction-fixed form
    for candidate in (t, _fix_line(t)):
        words = set(re.findall(r'[\u05d0-\u05ea]+', candidate))
        if words & _HEADER_SINGLES:          # any single strong header word
            return True
        if len(words & _HEADER_WORDS) >= 2:  # two or more header keywords
            return True
    return False
