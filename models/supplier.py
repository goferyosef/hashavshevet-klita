from dataclasses import dataclass, field
from typing import List
import uuid


@dataclass
class Supplier:
    name: str
    should_upload: bool = True
    vat_rate: float = 18.0       # 18 or 12 (= 2/3 of 18)
    aliases: List[str] = field(default_factory=list)
    notes: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "should_upload": self.should_upload,
            "vat_rate": self.vat_rate,
            "aliases": self.aliases,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Supplier":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data["name"],
            should_upload=data.get("should_upload", True),
            vat_rate=data.get("vat_rate", 18.0),
            aliases=data.get("aliases", []),
            notes=data.get("notes", ""),
        )
