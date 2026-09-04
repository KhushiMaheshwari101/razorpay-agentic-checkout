"""
Catalog schema — deliberately kept close to the schema.org `Product` pattern
(name, category, price, description, features) rather than inventing a
bespoke format, so the catalog stays interoperable with the kind of
agent-readable product data other buyer agents already expect.

Each product also carries a `provenance_checksum`: a SHA-256 hash of its
core fields. The Grounding Gate (see grounding/grounding_gate.py) uses this
to detect if a catalog entry was tampered with between indexing and
checkout — this is the FAISS provenance-tagging defense referenced in the
SoK paper on agentic-commerce security (Section 4.1.3 / S2I supply-chain
integrity vector).
"""

import hashlib
import json
from dataclasses import dataclass, field


@dataclass
class Product:
    id: str
    name: str
    category: str
    price_inr: int
    billing_cycle: str
    description: str
    features: list
    in_stock: bool
    provenance_checksum: str = field(default="", init=False)

    def __post_init__(self):
        self.provenance_checksum = self._compute_checksum()

    def _compute_checksum(self) -> str:
        core = f"{self.id}|{self.name}|{self.price_inr}|{self.billing_cycle}|{self.description}"
        return hashlib.sha256(core.encode("utf-8")).hexdigest()[:16]

    def verify_integrity(self) -> bool:
        """Re-derive the checksum and compare — catches silent tampering
        of price/name/billing_cycle after the product was first indexed."""
        return self.provenance_checksum == self._compute_checksum()

    def searchable_text(self) -> str:
        """Text blob used for embedding — what the buyer agent actually
        searches against."""
        features_str = ", ".join(self.features) if isinstance(self.features, list) else str(self.features)
        return f"{self.name}. {self.description} Category: {self.category}. Features: {features_str}."

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "price": self.price_inr,
            "price_inr": self.price_inr,
            "billing_cycle": self.billing_cycle,
            "description": self.description,
            "features": self.features,
            "in_stock": self.in_stock,
            "provenance_checksum": self.provenance_checksum,
        }



def load_catalog(path: str) -> list:
    with open(path, "r") as f:
        raw = json.load(f)
    return [Product(**item) for item in raw]


if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    catalog = load_catalog(os.path.join(here, "products.json"))
    for p in catalog:
        status = "OK" if p.verify_integrity() else "TAMPERED"
        print(f"[{status}] {p.id}: ₹{p.price_inr} checksum={p.provenance_checksum}")