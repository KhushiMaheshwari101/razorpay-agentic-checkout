"""
agent/buyer_agent.py & agent/executor.py
----------------------------------------
Complete Autonomous AI Buyer Agent Orchestrator.
Combines AP2 Mandate Chain + Grounding Gate + RBI ₹15,000 Step-Up + Razorpay Checkout + Receipt Chain.
"""

import time
import os
import uuid
from typing import Dict, Any, Optional, List

from mandate.kripke_state import (
    MandateState,
    transition,
    IllegalTransitionError,
    RBI_STEP_UP_THRESHOLD_INR,
)
from mandate.intent_mandate import IntentMandate
from mandate.cart_mandate import CartMandate
from mandate.payment_mandate import PaymentMandate
from mandate.chain import verify_chain
from mandate.crypto_signing import MandateSigner, verify_mandate_signature
from catalog.faiss_index import CatalogIndex
from catalog.schema import load_catalog, Product
from grounding.contradiction_detector import ContradictionDetector, check_response
from grounding.grounding_gate import verify_cart_grounding
from guardrails.rules import evaluate_guardrails, MAX_GLOBAL_SPEND_LIMIT
from guardrails.risk_vector import RiskVectorEngine
from guardrails.loop_detector import LoopDetector
from guardrails.failure_classifier import FailureClassifier
from checkout.fallback_mode import attempt_checkout, CheckoutResult, CheckoutMode
from audit.receipt_chain import ReceiptChain
from audit.recourse import DenialReason, generate_recourse
from audit.metrics import MetricsTracker


class BuyerAgent:
    def __init__(
        self,
        catalog_path: Optional[str] = None,
        user_id: str = "user_priya_01",
        default_max_spend: float = 25000.0,
    ):
        here = os.path.dirname(os.path.abspath(__file__))
        if catalog_path is None:
            catalog_path = os.path.join(here, "..", "catalog", "products.json")
        self.catalog_path = catalog_path
        self.user_id = user_id
        self.default_max_spend = default_max_spend

        # Cryptographic Ed25519 signer for AP2 Verifiable Credentials
        self.signer = MandateSigner()
        self.public_key_hex = self.signer.get_public_key_hex()

        # Core subsystems
        self.catalog_index = CatalogIndex(self.catalog_path)
        self.raw_catalog = load_catalog(self.catalog_path)
        self.catalog_dicts = [p.to_dict() for p in self.raw_catalog]


        # Core subsystems
        self.catalog_index = CatalogIndex(self.catalog_path)
        self.raw_catalog = load_catalog(self.catalog_path)
        self.catalog_dicts = [p.to_dict() for p in self.raw_catalog]
        
        self.contradiction_detector = ContradictionDetector()
        self.risk_engine = RiskVectorEngine()
        self.loop_detector = LoopDetector()
        self.failure_classifier = FailureClassifier()
        self.receipt_chain = ReceiptChain()
        self.metrics = MetricsTracker()

    def process_purchase_intent(
        self,
        user_query: str,
        user_max_spend: Optional[float] = None,
        step_up_consent_given: bool = False,
        pause_requested: bool = False,
        cancel_requested: bool = False,
    ) -> Dict[str, Any]:
        """
        End-to-end execution of a purchase query through the complete 3-layer architecture.
        """
        start_time = time.time()
        self.metrics.record_attempt()
        state = MandateState.CREATED

        max_spend = user_max_spend if user_max_spend is not None else self.default_max_spend

        # 0. Check Loop Detector (bypass if user is performing step-up re-consent)
        if step_up_consent_given:
            self.loop_detector.reset()

        if not step_up_consent_given and self.loop_detector.check_loop(user_query):
            self.metrics.record_denial(DenialReason.UNKNOWN)
            recourse = generate_recourse(DenialReason.UNKNOWN, "Duplicate query loop detected. Filter reset — please try again.")
            return {
                "success": False,
                "state": state.value,
                "error": "Loop detected",
                "recourse": recourse.as_dict(),
            }


        # 1. Draft and Confirm Intent Mandate
        intent_mandate = IntentMandate(
            user_id=self.user_id,
            max_spend_inr=max_spend,
            allowed_categories=["subscription"],
        )
        try:
            state = transition(state, "confirm_intent")
        except IllegalTransitionError as e:
            return {"success": False, "state": state.value, "error": str(e)}

        # Support user pause / cancel rights (RBI 2026 mandate requirement)
        if pause_requested:
            state = transition(state, "pause")
            return {"success": True, "state": state.value, "message": "Mandate paused by user."}
        if cancel_requested:
            state = transition(state, "cancel")
            return {"success": True, "state": state.value, "message": "Mandate cancelled by user."}

        # 2. Semantic Search in Catalog
        hits = self.catalog_index.search(user_query, top_k=2)
        if not hits:
            hits = [(self.raw_catalog[0], 0.5)]

        selected_product: Product = hits[0][0]
        reasoning = f"Matched user intent '{user_query}' with score {hits[0][1]:.3f}. Best tier fit in subscription catalog."

        # 3. Grounding Gate: verify item against catalog truth
        cart_item = {
            "id": selected_product.id,
            "product_id": selected_product.id,
            "name": selected_product.name,
            "price": selected_product.price_inr,
            "price_inr": selected_product.price_inr,
            "quantity": 1,
        }
        grounding_res = verify_cart_grounding([cart_item], self.catalog_dicts)
        if not grounding_res["is_grounded"]:
            self.metrics.record_denial(DenialReason.HALLUCINATION_BLOCKED)
            self.metrics.record_contradiction()
            recourse = generate_recourse(DenialReason.HALLUCINATION_BLOCKED, "; ".join(grounding_res["discrepancies"]))
            return {
                "success": False,
                "state": state.value,
                "error": "Grounding gate blocked unverified product",
                "discrepancies": grounding_res["discrepancies"],
                "recourse": recourse.as_dict(),
            }

        # 4. Contradiction Detector against user query
        contra_res = self.contradiction_detector.detect_contradictions(
            user_intent_text=user_query,
            cart_items=[cart_item],
            total_spend=selected_product.price_inr,
            max_spend_limit=max_spend,
        )
        if contra_res["is_contradictory"]:
            self.metrics.record_denial(DenialReason.HALLUCINATION_BLOCKED)
            self.metrics.record_contradiction()
            recourse = generate_recourse(DenialReason.HALLUCINATION_BLOCKED, "; ".join(contra_res["contradictions"]))
            return {
                "success": False,
                "state": state.value,
                "error": "Contradiction detected",
                "contradictions": contra_res["contradictions"],
                "recourse": recourse.as_dict(),
            }

        # 5. Build Cart Mandate
        cart_mandate = CartMandate(
            intent_mandate_hash=intent_mandate.mandate_hash,
            product_id=selected_product.id,
            product_name=selected_product.name,
            price_inr=selected_product.price_inr,
            reasoning=reasoning,
        )
        state = transition(state, "confirm_cart")

        # 6. Evaluate Guardrails & RBI ₹15,000 Step-Up
        guard_res = evaluate_guardrails(
            intent_max_spend=max_spend,
            cart_amount=selected_product.price_inr,
            product_category=selected_product.category,
            allowed_categories=intent_mandate.allowed_categories,
        )

        if not guard_res["approved"] and not guard_res["requires_step_up"]:
            self.metrics.record_denial(DenialReason.AMOUNT_MISMATCH)
            recourse = generate_recourse(DenialReason.AMOUNT_MISMATCH, "; ".join(guard_res["violations"]))
            return {
                "success": False,
                "state": state.value,
                "error": "Guardrail violation",
                "violations": guard_res["violations"],
                "recourse": recourse.as_dict(),
            }

        # Step-Up Flow
        is_step_up_needed = guard_res["requires_step_up"]
        if is_step_up_needed:
            self.metrics.record_step_up_triggered()
            state = transition(state, "require_step_up")

            if not step_up_consent_given:
                recourse = generate_recourse(
                    DenialReason.STEP_UP_REQUIRED,
                    f"Amount INR {selected_product.price_inr:,.0f} > INR {RBI_STEP_UP_THRESHOLD_INR:,.0f}"
                )
                return {
                    "success": False,
                    "state": state.value,
                    "requires_step_up": True,
                    "step_up_threshold": RBI_STEP_UP_THRESHOLD_INR,
                    "amount_inr": selected_product.price_inr,
                    "product": selected_product.to_dict(),
                    "intent_mandate": intent_mandate.to_dict(),
                    "cart_mandate": cart_mandate.to_dict(),
                    "message": "Step-up authentication required under RBI 2026 framework.",
                    "recourse": recourse.as_dict(),
                }
            else:
                state = transition(state, "step_up_confirmed", {"step_up_confirmed": True})
        else:
            state = transition(state, "proceed_low_value")

        # 7. Execute Checkout via Razorpay (with fallback)
        checkout_res: CheckoutResult = attempt_checkout(
            amount_inr=selected_product.price_inr,
            receipt=f"rcpt_{uuid.uuid4().hex[:8]}",
        )
        self.metrics.record_checkout_mode(checkout_res.mode.value)

        # 8. Build Payment Mandate
        payment_mandate = PaymentMandate(
            cart_mandate_hash=cart_mandate.mandate_hash,
            amount_inr=selected_product.price_inr,
            razorpay_order_id=checkout_res.order_id,
            step_up_confirmed=is_step_up_needed,
        )

        # 9. Verify full cryptographic mandate chain
        chain_valid = verify_chain(intent_mandate, cart_mandate, payment_mandate)
        if not chain_valid:
            self.metrics.record_denial(DenialReason.MANDATE_TAMPERED)
            recourse = generate_recourse(DenialReason.MANDATE_TAMPERED)
            return {
                "success": False,
                "state": state.value,
                "error": "Mandate chain verification failed",
                "recourse": recourse.as_dict(),
            }

        # 10. Complete state transition
        state = transition(state, "complete")

        # 11. Add to SHA-256 Receipt Chain
        receipt = self.receipt_chain.add_receipt(
            receipt_id=f"rcpt_{uuid.uuid4().hex[:8]}",
            mandate_chain_hash=payment_mandate.mandate_hash,
            checkout_order_id=checkout_res.order_id,
            checkout_mode=checkout_res.mode.value,
            amount_inr=selected_product.price_inr,
            grounding_passed=True,
        )

        latency = round(time.time() - start_time, 3)
        self.metrics.record_success(latency_sec=latency)
        self.loop_detector.reset()


        return {
            "success": True,
            "state": state.value,
            "product": selected_product.to_dict(),
            "amount_inr": selected_product.price_inr,
            "checkout_mode": checkout_res.mode.value,
            "checkout_order_id": checkout_res.order_id,
            "step_up_applied": is_step_up_needed,
            "latency_sec": latency,
            "mandates": {
                "intent_mandate": intent_mandate.to_dict(),
                "cart_mandate": cart_mandate.to_dict(),
                "payment_mandate": payment_mandate.to_dict(),
            },
            "receipt": receipt.to_dict(),
            "receipt_chain_valid": self.receipt_chain.verify_chain(),
        }


# Backwards compatibility alias
AgentExecutor = BuyerAgent


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    agent = BuyerAgent()
    res = agent.process_purchase_intent("I want the best subscription for a big family")
    print("Execution result:", res)
