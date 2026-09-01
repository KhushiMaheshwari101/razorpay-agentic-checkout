"""
test_p2k.py — Prompt-to-Kripke (state-machine) injection
---------------------------------
Attack shape: instead of attacking a tool call or a product description,
the attacker targets the STATE MACHINE itself — trying to force an
illegal transition (skip straight to COMPLETED, resurrect a CANCELLED
mandate, or bypass the RBI step-up gate) via a crafted "event" string
that an insecure implementation might interpret too literally (e.g.
via eval()/getattr() on untrusted input).

Defense under test: `transition()` is a strict allow-list lookup
against a hardcoded table — (current_state, event) -> next_state.
Anything not explicitly in the table raises IllegalTransitionError.
No event string, however it's phrased, can produce a transition that
isn't in the table.

Run: python3 test_p2k.py
"""

from __future__ import annotations

from typing import List, Tuple, Optional, Dict, Any

try:
    from mandate.kripke_state import MandateState, transition, IllegalTransitionError  # type: ignore
except ImportError:
    from _test_stubs import MandateState, transition, IllegalTransitionError


# ---------------------------------------------------------------------------
# Adversarial payloads: (starting_state, malicious_event, context)
# ---------------------------------------------------------------------------

P2K_ATTACKS: List[Tuple[MandateState, str, Optional[Dict[str, Any]]]] = [
    # 1. Skip straight from CREATED to COMPLETED — no intent, cart, or payment ever confirmed.
    (MandateState.CREATED, "complete", None),

    # 2. Resurrect a cancelled mandate straight into CONFIRMED.
    (MandateState.CANCELLED, "step_up_confirmed", {"step_up_confirmed": True}),

    # 3. Claim step-up was confirmed via the event NAME alone, without the
    #    context flag actually being set — this is the exact RBI-threshold
    #    bypass bug that was found and fixed earlier in this project.
    (MandateState.STEP_UP_PENDING, "step_up_confirmed", {"step_up_confirmed": False}),
    (MandateState.STEP_UP_PENDING, "step_up_confirmed", None),  # no context at all

    # 4. Classic injection payload disguised as an event string — tests that
    #    transition() does a plain dict lookup and never eval()s or does
    #    getattr() on attacker-controlled text.
    (MandateState.CREATED, "__class__", None),
    (MandateState.CREATED, "os.system('echo pwned')", None),
    (MandateState.CREATED, "'; DROP TABLE mandates; --", None),

    # 5. Skip CART_CONFIRMED entirely: try to go straight from
    #    INTENT_CONFIRMED to STEP_UP_PENDING.
    (MandateState.INTENT_CONFIRMED, "require_step_up", None),

    # 6. Re-enter a terminal state's "exit" transitions after completion —
    #    e.g. try to pause or cancel an already-COMPLETED mandate.
    (MandateState.COMPLETED, "pause", None),
    (MandateState.COMPLETED, "cancel", None),
]


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

def run() -> None:
    print("=== test_p2k.py — Prompt-to-Kripke state-machine injection ===\n")

    blocked = 0
    for i, (state, event, context) in enumerate(P2K_ATTACKS, start=1):
        try:
            result_state = transition(state, event, context)
            print(f"  [{i}] !! UNEXPECTED SUCCESS: {state.value} + {event!r} -> {result_state.value}")
        except IllegalTransitionError as e:
            blocked += 1
            print(f"  [{i}] blocked: {state.value} + {event!r} -> {e}")
        except Exception as e:
            # Any OTHER exception type (e.g. AttributeError from a getattr()-based
            # implementation) is itself a finding: it means untrusted input reached
            # something more dangerous than a controlled rejection.
            print(f"  [{i}] !! UNSAFE FAILURE MODE ({type(e).__name__}): {e}")
            raise

    attack_success_rate = 100 * (len(P2K_ATTACKS) - blocked) / len(P2K_ATTACKS)
    print(f"\n{blocked}/{len(P2K_ATTACKS)} malicious transitions blocked "
          f"(attack success rate = {attack_success_rate:.1f}%)")
    assert blocked == len(P2K_ATTACKS), "P2K guardrail FAILED to block an illegal transition"

    # --- Sanity check: the LEGITIMATE happy path still works end-to-end ---
    print("\n--- Sanity check: legitimate happy path still works ---")
    s = MandateState.CREATED
    s = transition(s, "confirm_intent")
    s = transition(s, "confirm_cart")
    s = transition(s, "require_step_up")
    s = transition(s, "step_up_confirmed", {"step_up_confirmed": True})
    s = transition(s, "complete")
    assert s is MandateState.COMPLETED
    print(f"Legitimate flow reached: {s.value}")

    # --- Sanity check: low-value path (no step-up needed) still works ---
    s2 = MandateState.CART_CONFIRMED
    s2 = transition(s2, "proceed_low_value")
    assert s2 is MandateState.CONFIRMED
    print(f"Legitimate low-value flow reached: {s2.value}")

def test_p2k() -> None:
    run()


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    run()