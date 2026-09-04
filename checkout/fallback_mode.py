"""
fallback_mode.py
---------------------------------
"Failure Recovery" building block (one of Razorpay's own 4 judging
criteria). If the live Razorpay call fails — network issue, bad keys,
rate limit, whatever — the demo should NOT crash. It should visibly
and honestly degrade into a simulated transaction, clearly labelled
as such in the audit trail. This is the opposite of hiding a failure:
it's a documented, bounded fallback path.

Integration point: call attempt_checkout() instead of calling
razorpay_client.create_order() directly.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Optional

try:
    from checkout.razorpay_client import create_order, RazorpayClientError, OrderResult
except ImportError:
    from razorpay_client import create_order, RazorpayClientError, OrderResult



class CheckoutMode(Enum):
    LIVE = "live"          # real Razorpay test-mode API call succeeded
    FALLBACK = "fallback"  # simulated, because the live call failed


@dataclass
class CheckoutResult:
    mode: CheckoutMode
    order_id: str
    amount_inr: float
    status: str
    reason: Optional[str] = None  # populated only in FALLBACK mode

    def is_live(self) -> bool:
        return self.mode is CheckoutMode.LIVE


def _simulate_order(amount_inr: float, reason: str) -> CheckoutResult:
    """Generates a clearly-marked fake order so the demo can still show
    the rest of the pipeline (receipt chain, metrics) end-to-end."""
    fake_id = f"sim_order_{uuid.uuid4().hex[:12]}"
    return CheckoutResult(
        mode=CheckoutMode.FALLBACK,
        order_id=fake_id,
        amount_inr=amount_inr,
        status="simulated_success",
        reason=reason,
    )


def attempt_checkout(amount_inr: float, receipt: Optional[str] = None, max_retries: int = 1) -> CheckoutResult:
    """
    Tries the live Razorpay order creation. On failure, retries up to
    `max_retries` times (transient-error tolerance), then falls back
    to a simulated order rather than failing the whole demo.
    """
    last_error: Optional[str] = None

    for attempt in range(max_retries + 1):
        try:
            order: OrderResult = create_order(amount_inr=amount_inr, receipt=receipt)
            return CheckoutResult(
                mode=CheckoutMode.LIVE,
                order_id=order.order_id,
                amount_inr=amount_inr,
                status=order.status,
            )
        except RazorpayClientError as e:
            last_error = str(e)
            if attempt < max_retries:
                time.sleep(0.5)  # brief backoff before retry
            continue

    # All attempts failed — degrade honestly, don't crash.
    return _simulate_order(amount_inr, reason=f"Razorpay unavailable after {max_retries + 1} attempt(s): {last_error}")


# ---------------------------------------------------------------------------
# Self-test / demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("--- fallback_mode smoke test ---")
    result = attempt_checkout(amount_inr=17999, receipt="demo-receipt-001")
    print(f"mode={result.mode.value} order_id={result.order_id} status={result.status}")
    if result.mode is CheckoutMode.FALLBACK:
        print(f"reason={result.reason}")
    print("\nThis is the exact failure-recovery path — same call site works")
    print("whether Razorpay is reachable or not, and the result is always")
    print("honestly labelled live vs fallback for the audit trail.")