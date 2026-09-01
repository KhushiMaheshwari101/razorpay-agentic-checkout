"""
razorpay_client.py
---------------------------------
Thin wrapper around Razorpay's TEST-MODE Orders API.

Requires:
    pip install razorpay python-dotenv

.env (never commit this — add to .gitignore):
    RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxx
    RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxx

This module ONLY talks to Razorpay. It does not decide whether a
transaction *should* happen — that decision belongs to your mandate
chain (amount match, RBI step-up check, guardrails) which must run
BEFORE create_order() is called. This file trusts its caller.

On any failure (missing keys, network error, API error) it raises
RazorpayClientError — checkout.fallback_mode is expected to catch this
and degrade gracefully rather than crash the demo.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional; env vars can also be set directly


class RazorpayClientError(Exception):
    """Raised whenever the Razorpay call cannot be completed."""


@dataclass
class OrderResult:
    order_id: str
    amount_paise: int
    currency: str
    status: str
    receipt: Optional[str] = None


def _get_client():
    try:
        import razorpay
    except ImportError as e:
        raise RazorpayClientError(
            "razorpay SDK not installed. Run: pip install razorpay"
        ) from e

    key_id = os.environ.get("RAZORPAY_KEY_ID")
    key_secret = os.environ.get("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret:
        raise RazorpayClientError(
            "Missing RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET env vars. "
            "Set them in a .env file (test-mode keys only)."
        )
    if not key_id.startswith("rzp_test_"):
        raise RazorpayClientError(
            "Refusing to run: key_id does not look like a TEST key "
            "(expected prefix 'rzp_test_'). This project must never touch live keys."
        )

    return razorpay.Client(auth=(key_id, key_secret))


def create_order(amount_inr: float, currency: str = "INR", receipt: Optional[str] = None) -> OrderResult:
    """
    Creates a Razorpay order for `amount_inr` rupees (converted to paise,
    since Razorpay's API is paise-denominated).
    """
    if amount_inr <= 0:
        raise RazorpayClientError(f"Invalid amount for order creation: {amount_inr}")

    client = _get_client()
    amount_paise = int(round(amount_inr * 100))

    try:
        order = client.order.create({
            "amount": amount_paise,
            "currency": currency,
            "receipt": receipt or "auto-generated",
            "payment_capture": 1,
        })
    except Exception as e:  # razorpay SDK raises its own error types
        raise RazorpayClientError(f"Razorpay order creation failed: {e}") from e

    return OrderResult(
        order_id=order["id"],
        amount_paise=order["amount"],
        currency=order["currency"],
        status=order["status"],
        receipt=order.get("receipt"),
    )


def fetch_payment(payment_id: str) -> dict:
    client = _get_client()
    try:
        return client.payment.fetch(payment_id)
    except Exception as e:
        raise RazorpayClientError(f"Could not fetch payment {payment_id}: {e}") from e


def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """
    Verifies the payment signature Razorpay sends back after checkout,
    proving the payment genuinely belongs to this order and wasn't spoofed.
    """
    client = _get_client()
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        })
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Self-test / demo (does NOT hit the network unless keys are configured)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("--- razorpay_client smoke test ---")
    try:
        result = create_order(amount_inr=17999, receipt="demo-receipt-001")
        print(f"Order created: {result}")
    except RazorpayClientError as e:
        # Expected in this sandbox — no real test keys configured here.
        print(f"Expected failure (no live test-mode keys in this environment): {e}")
        print("This is the exact condition checkout.fallback_mode is built to catch.")