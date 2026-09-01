"""
mandate/payment_mandate.py
--------------------------
Payment Mandate — third and final link in the AP2 chain.
Authorizes payment execution on Razorpay, hash-linked to Cart Mandate.
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
class PaymentMandate:
    cart_mandate_hash: str
    amount_inr: float
    razorpay_order_id: str
    step_up_confirmed: bool
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
    from mandate.cart_mandate import CartMandate
    intent = IntentMandate(user_id="user-priya-01", max_spend_inr=20000, allowed_categories=["subscription"])
    cart = CartMandate(
        intent_mandate_hash=intent.mandate_hash,
        product_id="sf-family-annual",
        product_name="StreamFlix Family Annual Bundle",
        price_inr=17999,
        reasoning="User asked for the best plan for a big family.",
    )
    payment = PaymentMandate(
        cart_mandate_hash=cart.mandate_hash,
        amount_inr=17999,
        razorpay_order_id="order_TEST123",
        step_up_confirmed=True,
    )
    print("Payment hash:", payment.mandate_hash)
    print("Linked to correct cart:", payment.cart_mandate_hash == cart.mandate_hash)
    print("Integrity OK:", payment.verify_integrity())