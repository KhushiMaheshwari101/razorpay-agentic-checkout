"""
recourse.py
---------------------------------
When a transaction is denied/blocked, don't just say "denied" — tell
the user exactly what would need to change for it to succeed. This is
deliberately rule-based (no LIME/SHAP, no ML explainability stack —
Tier 1/2 scope decision). Each denial reason maps to a concrete,
actionable next step.

Integration point: whichever module blocks a transaction (mandate
chain amount-check, RBI step-up check, grounding gate, stock check)
should raise/return one of these DenialReason values, then call
generate_recourse() to produce the user-facing message.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any


class DenialReason(Enum):
    AMOUNT_MISMATCH = "amount_mismatch"          # cart price != payment amount
    STEP_UP_REQUIRED = "step_up_required"        # RBI ₹15,000 AFA threshold not confirmed
    INSUFFICIENT_STOCK = "insufficient_stock"
    HALLUCINATION_BLOCKED = "hallucination_blocked"   # grounding gate caught a contradiction
    MANDATE_EXPIRED = "mandate_expired"
    MANDATE_TAMPERED = "mandate_tampered"         # hash-chain verification failed
    UNKNOWN = "unknown"


@dataclass
class RecourseMessage:
    reason: DenialReason
    user_message: str
    actionable_step: str
    retryable: bool

    def as_dict(self) -> Dict[str, Any]:
        return {
            "reason": self.reason.value,
            "user_message": self.user_message,
            "actionable_step": self.actionable_step,
            "retryable": self.retryable,
        }


# RBI E-Mandate Framework AFA (Additional Factor of Authentication) threshold.
RBI_STEP_UP_THRESHOLD_INR = 15000


_RECOURSE_TEMPLATES = {
    DenialReason.AMOUNT_MISMATCH: (
        "The payment amount doesn't match your cart total, so this transaction was blocked for your safety.",
        "Please re-confirm your cart and retry — the payment amount must exactly match the cart price.",
        True,
    ),
    DenialReason.STEP_UP_REQUIRED: (
        f"This transaction is above ₹{RBI_STEP_UP_THRESHOLD_INR:,}, so RBI rules require an extra confirmation step.",
        "Please complete step-up authentication (OTP/biometric confirmation) to proceed.",
        True,
    ),
    DenialReason.INSUFFICIENT_STOCK: (
        "This item is no longer in stock.",
        "Choose a different quantity, a similar in-stock item, or check back later.",
        False,
    ),
    DenialReason.HALLUCINATION_BLOCKED: (
        "We caught a mismatch between what was said about this product and the actual catalog data, so we paused the transaction to be safe.",
        "Please refresh the product details and try again.",
        True,
    ),
    DenialReason.MANDATE_EXPIRED: (
        "Your purchase confirmation has expired.",
        "Please restart the checkout so a fresh, time-valid mandate can be issued.",
        True,
    ),
    DenialReason.MANDATE_TAMPERED: (
        "We detected an integrity issue with this transaction's record and blocked it as a precaution.",
        "Please start a new checkout — this specific attempt cannot be recovered for safety reasons.",
        False,
    ),
    DenialReason.UNKNOWN: (
        "This transaction could not be completed.",
        "Please try again, or contact support if the issue persists.",
        True,
    ),
}


def generate_recourse(reason: DenialReason, extra_context: Optional[str] = None) -> RecourseMessage:
    user_message, actionable_step, retryable = _RECOURSE_TEMPLATES[reason]
    if extra_context:
        user_message = f"{user_message} ({extra_context})"
    return RecourseMessage(
        reason=reason,
        user_message=user_message,
        actionable_step=actionable_step,
        retryable=retryable,
    )


# ---------------------------------------------------------------------------
# Self-test / demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("--- recourse.py demo: all denial reasons ---")
    for reason in DenialReason:
        msg = generate_recourse(reason)
        print(f"\n{reason.value}:")
        print(f"  message : {msg.user_message}")
        print(f"  action  : {msg.actionable_step}")
        print(f"  retryable: {msg.retryable}")

    print("\n--- With extra context ---")
    msg = generate_recourse(
        DenialReason.STEP_UP_REQUIRED,
        extra_context="Transaction amount: ₹17,999",
    )
    print(msg.user_message)

    assert generate_recourse(DenialReason.AMOUNT_MISMATCH).retryable is True
    assert generate_recourse(DenialReason.INSUFFICIENT_STOCK).retryable is False
    print("\nrecourse.py self-tests passed.")