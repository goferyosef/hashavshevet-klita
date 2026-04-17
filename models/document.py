from dataclasses import dataclass, field


@dataclass
class DocumentRecord:
    file_name: str = ""
    folder: str = ""
    supplier: str = ""
    doc_type: str = ""          # "חשבונית" | "קבלה"
    date: str = ""
    total_amount: float = 0.0
    vat_amount: float = 0.0
    vat_rate: float = 0.0
    action: str = ""            # "הועלה" | "דולג" | "שגיאה"
    timestamp: str = ""
    doc_number: str = ""
    error_msg: str = ""
