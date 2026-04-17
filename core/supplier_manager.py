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

    def import_from_text(self, text: str):
        """Parse one supplier name per line and add any not already present."""
        existing_names = {s.name.strip().lower() for s in self.suppliers}
        added = 0
        for line in text.splitlines():
            name = line.strip()
            if name and name.lower() not in existing_names:
                self.add(Supplier(name=name))
                existing_names.add(name.lower())
                added += 1
        return added
