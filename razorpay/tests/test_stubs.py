"""
_test_stubs.py
---------------------------------
Minimal stand-ins for your real mandate/kripke_state.py and mandate/chain.py,
used ONLY so these adversarial test files can run standalone in this sandbox
(where your actual mandate/ modules aren't present). Every test file tries
to import your REAL modules FIRST and only falls back to these stubs.

When you drop these test files into your actual repo (tests/ next to
mandate/, catalog/, checkout/, audit/), the real imports will succeed and
these stubs are simply never used.

If your real MandateState / transition() / MandateChain names or signatures
differ from what's assumed here, adjust the import lines at the top of each
test file to match — the test LOGIC (the attacks themselves) stays valid
regardless of exact naming.
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

# Explicit allow-list of (current_state, event) -> next_state.
# Anything not in this table is illegal — this is the whole point of a
# Kripke-style state machine: transitions are enumerated, not inferred.
_TRANSITIONS = {
    (MandateState.CREATED, "confirm_intent"): MandateState.INTENT_CONFIRMED,
    (MandateState.INTENT_CONFIRMED, "confirm_cart"): MandateState.CART_CONFIRMED,
    (MandateState.CART_CONFIRMED, "proceed_low_value"): MandateState.CONFIRMED,
    (MandateState.CART_CONFIRMED, "require_step_up"): MandateState.STEP_UP_PENDING,
    (MandateState.STEP_UP_PENDING, "step_up_confirmed"): MandateState.CONFIRMED,
    (MandateState.CONFIRMED, "complete"): MandateState.COMPLETED,
    # PAUSE reachable from any non-terminal state
    (MandateState.CREATED, "pause"): MandateState.PAUSED,
    (MandateState.INTENT_CONFIRMED, "pause"): MandateState.PAUSED,
    (MandateState.CART_CONFIRMED, "pause"): MandateState.PAUSED,
    (MandateState.STEP_UP_PENDING, "pause"): MandateState.PAUSED,
    # resume back to where it was paused from (simplified: resume -> CART_CONFIRMED)
    (MandateState.PAUSED, "resume"): MandateState.CART_CONFIRMED,
    # CANCEL reachable from any non-terminal state
    (MandateState.CREATED, "cancel"): MandateState.CANCELLED,
    (MandateState.INTENT_CONFIRMED, "cancel"): MandateState.CANCELLED,
    (MandateState.CART_CONFIRMED, "cancel"): MandateState.CANCELLED,
    (MandateState.STEP_UP_PENDING, "cancel"): MandateState.CANCELLED,
    (MandateState.PAUSED, "cancel"): MandateState.CANCELLED,
}


def transition(current: MandateState, event: str, context: Optional[Dict[str, Any]] = None) -> MandateState:
    """
    Strict, allow-list-only transition function.

    Security-critical property: `event` is an untrusted string (it may
    originate from parsed LLM output or user input). This function must
    NEVER use eval(), getattr(), or dynamic attribute/dict lookups keyed
    directly by the raw event string against sensitive namespaces — only
    a plain dict membership check against a fixed, hardcoded table.
    """
    context = context or {}

    if not isinstance(current, MandateState) or not isinstance(event, str):
        raise IllegalTransitionError(f"Malformed transition input: state={current!r} event={event!r}")

    key = (current, event)
    if key not in _TRANSITIONS:
        raise IllegalTransitionError(f"Illegal transition: {current.value} + '{event}'")

    next_state = _TRANSITIONS[key]

    # Extra business rule (this is the RBI step-up enforcement bug fixed earlier):
    # STEP_UP_PENDING -> CONFIRMED is only allowed if the caller has genuinely
    # confirmed step-up, not merely because the event string says so.
    if key == (MandateState.STEP_UP_PENDING, "step_up_confirmed"):
        if context.get("step_up_confirmed") is not True:
            raise IllegalTransitionError(
                "step_up_confirmed event received but context.step_up_confirmed is not True — "
                "refusing to bypass RBI AFA requirement."
            )

    return next_state