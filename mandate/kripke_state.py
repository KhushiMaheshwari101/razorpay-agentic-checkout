"""
mandate/kripke_state.py
-----------------------
Kripke-style finite state machine for AP2 Mandates.
Enforces the mandatory AP2 lifecycle + RBI Digital Payments E-Mandate Framework 2026
(PAUSE/CANCEL rights and ₹15,000 AFA step-up validation).
"""

from __future__ import annotations
from enum import Enum
from typing import Optional, Dict, Any


class IllegalTransitionError(Exception):
    pass


class MandateState(Enum):
    CREATED = "CREATED"
    INTENT_CONFIRMED = "INTENT_CONFIRMED"
    CART_CONFIRMED = "CART_CONFIRMED"
    STEP_UP_PENDING = "STEP_UP_PENDING"
    CONFIRMED = "CONFIRMED"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


RBI_STEP_UP_THRESHOLD_INR = 15000

# Strict allow-list of (current_state, event) -> next_state
_TRANSITIONS = {
    (MandateState.CREATED, "confirm_intent"): MandateState.INTENT_CONFIRMED,
    (MandateState.INTENT_CONFIRMED, "confirm_cart"): MandateState.CART_CONFIRMED,
    (MandateState.CART_CONFIRMED, "proceed_low_value"): MandateState.CONFIRMED,
    (MandateState.CART_CONFIRMED, "require_step_up"): MandateState.STEP_UP_PENDING,
    (MandateState.STEP_UP_PENDING, "step_up_confirmed"): MandateState.CONFIRMED,
    (MandateState.CONFIRMED, "complete"): MandateState.COMPLETED,
    # PAUSE reachable from any non-terminal state (RBI 2026 requirement)
    (MandateState.CREATED, "pause"): MandateState.PAUSED,
    (MandateState.INTENT_CONFIRMED, "pause"): MandateState.PAUSED,
    (MandateState.CART_CONFIRMED, "pause"): MandateState.PAUSED,
    (MandateState.STEP_UP_PENDING, "pause"): MandateState.PAUSED,
    # Resume from paused state
    (MandateState.PAUSED, "resume"): MandateState.CART_CONFIRMED,
    # CANCEL reachable from any non-terminal state (RBI 2026 requirement)
    (MandateState.CREATED, "cancel"): MandateState.CANCELLED,
    (MandateState.INTENT_CONFIRMED, "cancel"): MandateState.CANCELLED,
    (MandateState.CART_CONFIRMED, "cancel"): MandateState.CANCELLED,
    (MandateState.STEP_UP_PENDING, "cancel"): MandateState.CANCELLED,
    (MandateState.PAUSED, "cancel"): MandateState.CANCELLED,
}


def transition(
    current: MandateState,
    event: str,
    context: Optional[Dict[str, Any]] = None
) -> MandateState:
    context = context or {}

    if not isinstance(current, MandateState) or not isinstance(event, str):
        raise IllegalTransitionError(f"Malformed transition input: state={current!r} event={event!r}")

    key = (current, event)
    if key not in _TRANSITIONS:
        raise IllegalTransitionError(f"Illegal transition: {current.value} + '{event}'")

    next_state = _TRANSITIONS[key]

    # RBI Step-Up enforcement: STEP_UP_PENDING -> CONFIRMED requires context validation
    if key == (MandateState.STEP_UP_PENDING, "step_up_confirmed"):
        if context.get("step_up_confirmed") is not True:
            raise IllegalTransitionError(
                "step_up_confirmed event received but context.step_up_confirmed is not True — "
                "refusing to bypass RBI AFA requirement."
            )

    return next_state
