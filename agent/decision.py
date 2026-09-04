"""
Agent Decision – evaluates runtime safety policies, state permissions, 
and constraint enforcement before action execution.
"""

from typing import Dict, Any, List

class AgentDecisionEngine:
    def __init__(self, default_spend_limit: float = 5000.0):
        self.default_spend_limit = default_spend_limit
        # Strict state transition rules (Kripke-style guardrails aligned with planner states)
        self.allowed_transitions = {
            "INITIAL": ["INTENT_COLLECTED", "INITIAL"],
            "INTENT_COLLECTED": ["GROUNDING_VERIFIED", "INITIAL"],
            "GROUNDING_VERIFIED": ["RISK_EVALUATED", "COMPLETED", "INITIAL"],
            "RISK_EVALUATED": ["COMPLETED", "INITIAL"],
            "COMPLETED": ["INITIAL"]
        }

    def evaluate_transition(self, current_state: str, target_state: str) -> Dict[str, Any]:
        """Validates if moving from current_state to target_state is permitted."""
        if not current_state or not target_state:
            return {"allowed": False, "reason": "State parameters cannot be empty."}

        safe_current = str(current_state).strip().upper()
        safe_target = str(target_state).strip().upper()

        if safe_current not in self.allowed_transitions:
            return {
                "allowed": False,
                "reason": f"Unknown source state: '{safe_current}'."
            }

        valid_next_states = self.allowed_transitions[safe_current]
        if safe_target in valid_next_states:
            return {"allowed": True, "reason": "Transition permitted."}

        return {
            "allowed": False,
            "reason": f"Policy violation: Cannot transition from '{safe_current}' to '{safe_target}'."
        }

    def evaluate_grounding_gate(self, retrieved_products: List[Dict[str, Any]]) -> bool:
        """Ensures execution proceeds only if products carry valid catalog provenance."""
        if not retrieved_products or not isinstance(retrieved_products, list) or len(retrieved_products) == 0:
            return False
        
        for p in retrieved_products:
            if not isinstance(p, dict) or "provenance_source" not in p or not p["provenance_source"]:
                return False
        return True

    def evaluate_budget_constraint(self, products: List[Dict[str, Any]], custom_limit: float = None) -> Dict[str, Any]:
        """Evaluates whether total cart items exceed user or system spend limits."""
        limit = custom_limit if custom_limit is not None else self.default_spend_limit
        total_cost = sum(p.get("price", 0) for p in products if isinstance(p, dict))
        
        if total_cost > limit:
            return {
                "passed": False,
                "total_cost": total_cost,
                "limit": limit,
                "reason": f"Budget violation: Total cost INR {total_cost} exceeds limit of INR {limit}."
            }
        return {
            "passed": True,
            "total_cost": total_cost,
            "limit": limit,
            "reason": "Within budget constraints."
        }


if __name__ == "__main__":
    engine = AgentDecisionEngine()
    print(engine.evaluate_transition("INITIAL", "GROUNDING_VERIFIED"))