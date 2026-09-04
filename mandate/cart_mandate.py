"""
mandate/cart_mandate.py
-----------------------
Cart Mandate — second link in the AP2 chain.
Records selected product, price, and explainable decision reasoning.
"""

import time
from dataclasses import dataclass, field, asdict
from typing import Dict, Any

try:
    from mandate.hashing import compute_hash
except ImportError:
    try:
        from .hashing import compute_hash
    except ImportError:
        from hashing import compute_hash


@dataclass
class CartMandate:
    intent_mandate_hash: str
    product_id: str
    product_name: str
    price_inr: float
    reasoning: str
    created_at: float = field(default_factory=time.time)
    mandate_hash: str = field(default="", init=False)

    def __post_init__(self):
        self.mandate_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        payload = {k: v for k, v in asdict(self).items() if k != "mandate_hash"}
        return compute_hash(payload)

    def verify_integrity(self) -> bool:
        return self.mandate_hash == self._compute_hash()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


if __name__ == "__main__":
    from mandate.intent_mandate import IntentMandate
    intent = IntentMandate(user_id="user-priya-01", max_spend_inr=20000, allowed_categories=["subscription"])
    cart = CartMandate(
        intent_mandate_hash=intent.mandate_hash,
        product_id="sf-family-annual",
        product_name="StreamFlix Family Annual Bundle",
        price_inr=17999,
        reasoning="User asked for the best plan for a big family; only 6-screen option in catalog.",
    )
    print("Cart hash:", cart.mandate_hash)
    print("Linked to correct intent:", cart.intent_mandate_hash == intent.mandate_hash)
    print("Integrity OK:", cart.verify_integrity())
    cart.price_inr = 1  # tamper
    print("Integrity OK after tampering:", cart.verify_integrity())