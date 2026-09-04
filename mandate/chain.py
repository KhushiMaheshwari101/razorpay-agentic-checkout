"""
mandate/chain.py & chain.py
---------------------------
Chain-level verification — ties Intent, Cart, and Payment Mandates
together and checks the full chain in one call.
"""

from __future__ import annotations

try:
    from mandate.intent_mandate import IntentMandate
    from mandate.cart_mandate import CartMandate
    from mandate.payment_mandate import PaymentMandate
except ImportError:
    from intent_mandate import IntentMandate
    from cart_mandate import CartMandate
    from payment_mandate import PaymentMandate


def verify_chain(intent: IntentMandate, cart: CartMandate, payment: PaymentMandate) -> bool:
    """
    Verifies:
    1) Each mandate's internal hash matches its fields (no post-creation mutation)
    2) Cart Mandate points to Intent Mandate hash
    3) Payment Mandate points to Cart Mandate hash
    4) Payment amount matches Cart price exactly
    5) Cart price does not exceed Intent max spend
    6) If payment > ₹15,000, step_up_confirmed must be True
    """
    if not (intent.verify_integrity() and cart.verify_integrity() and payment.verify_integrity()):
        return False
    if cart.intent_mandate_hash != intent.mandate_hash:
        return False
    if payment.cart_mandate_hash != cart.mandate_hash:
        return False
    if abs(payment.amount_inr - cart.price_inr) > 0.01:
        return False
    if cart.price_inr > intent.max_spend_inr:
        return False
    if payment.amount_inr > 15000 and not payment.step_up_confirmed:
        return False
    return True


if __name__ == "__main__":
    intent = IntentMandate(user_id="user-priya-01", max_spend_inr=20000, allowed_categories=["subscription"])
    cart = CartMandate(
        intent_mandate_hash=intent.mandate_hash,
        product_id="sf-family-annual",
        product_name="StreamFlix Family Annual Bundle",
        price_inr=17999,
        reasoning="User asked for the best plan for a big family; only 6-screen option in catalog.",
    )
    payment = PaymentMandate(
        cart_mandate_hash=cart.mandate_hash,
        amount_inr=17999,
        razorpay_order_id="order_TEST123",
        step_up_confirmed=True,
    )

    print("Chain valid (before tampering):", verify_chain(intent, cart, payment))
    cart.price_inr = 1  # tamper
    print("Chain valid (after tampering cart.price_inr):", verify_chain(intent, cart, payment))