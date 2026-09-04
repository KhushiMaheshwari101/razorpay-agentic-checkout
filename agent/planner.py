"""
Agent Planner – orchestrates execution steps with precise Kripke state 
transition enforcement, regex word-boundary checks, and robust state projection.
"""

from typing import Dict, Any, List
import re

class AgentPlanner:
    def __init__(self):
        self.supported_actions = {
            "PARSE_INTENT",
            "RETRIEVE_CATALOG",
            "VERIFY_GROUNDING",
            "CHECK_CONTRADICTIONS",
            "EVALUATE_RISK",
            "EXECUTE_CHECKOUT"
        }
        
        # Valid states recognized by the planning engine
        self.recognized_states = {
            "INITIAL",
            "INTENT_COLLECTED",
            "GROUNDING_VERIFIED",
            "RISK_EVALUATED",
            "CHECKOUT_READY",
            "COMPLETED"
        }

    def create_execution_plan(self, user_query: str, current_state: str = "INITIAL") -> Dict[str, Any]:
        """
        Deconstructs user queries into sequential execution steps while strictly 
        enforcing Kripke state permissions and computing next state transitions.
        """
        if not isinstance(user_query, str) or not user_query.strip():
            return {
                "status": "ERROR",
                "message": "Invalid or empty user query provided for planning."
            }

        safe_state = str(current_state).strip().upper() if current_state else "INITIAL"
        
        if safe_state not in self.recognized_states:
            return {
                "status": "ERROR",
                "current_state": safe_state,
                "message": f"State validation error: '{safe_state}' is not a recognized Kripke state."
            }

        query_lower = user_query.lower()
        steps = []
        step_counter = 1

        def add_step(action_name: str, description: str):
            nonlocal step_counter
            if action_name not in self.supported_actions:
                raise ValueError(f"Unsupported action attempted: {action_name}")
            steps.append({
                "step_id": step_counter,
                "action": action_name,
                "description": description
            })
            step_counter += 1

        # Helper for precise word-boundary keyword matching
        def contains_keyword(text: str, keywords: List[str]) -> bool:
            return any(re.search(rf"\b{kw}\b", text) for kw in keywords)

        # Step 1: Always parse intent and constraints first
        add_step("PARSE_INTENT", "Extract product preference, quantity, and negative constraints from user text.")

        # Step 2: Catalog Retrieval & Grounding checks using word boundaries
        catalog_keywords = ["want", "buy", "get", "search", "show", "price", "board", "sensor"]
        if contains_keyword(query_lower, catalog_keywords):
            add_step("RETRIEVE_CATALOG", "Query FAISS index and product catalog for matching items with provenance tags.")
            add_step("VERIFY_GROUNDING", "Run grounding gate check to prevent hallucinations against products.json.")
            add_step("CHECK_CONTRADICTIONS", "Run contradiction detector against negative constraints and user spend limits.")

        # Step 3: Checkout and Risk Evaluation
        checkout_keywords = ["pay", "checkout", "purchase"]
        if contains_keyword(query_lower, checkout_keywords):
            if safe_state in ["INITIAL", "INTENT_COLLECTED"]:
                return {
                    "status": "BLOCKED",
                    "current_state": safe_state,
                    "message": f"State transition violation: Cannot execute checkout from state '{safe_state}' without prior grounding verification."
                }
                
            add_step("EVALUATE_RISK", "Compute multi-dimensional risk score and check RBI step-up rules.")
            add_step("EXECUTE_CHECKOUT", "Initiate secure transaction through Razorpay client with hash-linked audit logging.")

        # Dynamic state projection based on generated actions
        next_target_state = safe_state
        action_names = [s["action"] for s in steps]
        
        if "EXECUTE_CHECKOUT" in action_names:
            next_target_state = "COMPLETED"
        elif "VERIFY_GROUNDING" in action_names or "CHECK_CONTRADICTIONS" in action_names:
            next_target_state = "GROUNDING_VERIFIED"
        elif "RETRIEVE_CATALOG" in action_names:
            next_target_state = "INTENT_COLLECTED"

        return {
            "status": "SUCCESS",
            "current_state": safe_state,
            "next_target_state": next_target_state,
            "total_steps": len(steps),
            "execution_plan": steps
        }


if __name__ == "__main__":
    planner = AgentPlanner()
    plan = planner.create_execution_plan(
        user_query="I want an ESP32 board and let's checkout.",
        current_state="GROUNDING_VERIFIED"
    )
    import json
    print(json.dumps(plan, indent=2))