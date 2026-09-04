"""
Failure Classifier – categorizes agent runtime failures into deterministic 
and probabilistic categories using safe type coercion and combined context analysis.
"""

from typing import Dict, Any

class FailureClassifier:
    def __init__(self):
        self.deterministic_types = {
            "GUARDRAIL_VIOLATION",
            "GROUNDING_DISCREPANCY",
            "LOOP_DETECTED",
            "SCHEMA_VALIDATION_ERROR",
            "RBI_MANDATE_BLOCK",
            "UNAUTHORIZED_CATEGORY"
        }
        self.probabilistic_types = {
            "SEMANTIC_DRIFT",
            "HALLUCINATION_SUSPECTED",
            "VAGUE_TOOL_RESPONSE",
            "LOW_CONFIDENCE_PLAN"
        }

    def classify(self, error_code: Any, error_message: str = "") -> Dict[str, Any]:
        """
        Classifies an incoming error code and message into a deterministic or probabilistic 
        category with safe type coercion and a recommended recovery action.
        """
        # Safely coerce error_code to string to handle integers, enums, or exceptions gracefully
        if error_code is None:
            code_str = ""
        else:
            code_str = str(error_code).strip().upper()

        msg_str = error_message.strip().upper() if isinstance(error_message, str) else ""
        combined_context = f"{code_str} {msg_str}"

        if not code_str and not msg_str:
            return {
                "category": "UNKNOWN",
                "nature": "UNCLASSIFIED",
                "recovery_strategy": "manual_review"
            }

        # Check against sets or keyword heuristics in combined context
        if code_str in self.deterministic_types or any(dt in combined_context for dt in ["RULE", "GROUNDING", "LOOP", "SCHEMA", "BLOCK", "VIOLATION"]):
            return {
                "category": code_str or "DETERMINISTIC_ERROR",
                "nature": "DETERMINISTIC",
                "recovery_strategy": "algorithmic_correction_or_abort"
            }
        elif code_str in self.probabilistic_types or any(pt in combined_context for pt in ["DRIFT", "HALLUCINATION", "VAGUE", "CONFIDENCE", "PROBABILITY"]):
            return {
                "category": code_str or "PROBABILISTIC_ERROR",
                "nature": "PROBABILISTIC",
                "recovery_strategy": "prompt_refinement_or_retrieval_retry"
            }
        else:
            return {
                "category": code_str or "UNKNOWN_ERROR",
                "nature": "DETERMINISTIC",
                "recovery_strategy": "strict_block"
            }


if __name__ == "__main__":
    print("--- Testing Fully Hardened Failure Classifier ---")
    classifier = FailureClassifier()
    print(classifier.classify(400, "Bad Request Rule Violation"))
    print(classifier.classify("HALLUCINATION_SUSPECTED", "Model output seems uncertain"))