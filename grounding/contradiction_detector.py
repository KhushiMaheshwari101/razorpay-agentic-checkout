"""
Contradiction Detector – uses refined regex pattern matching and safe type coercion 
to identify direct contradictions between user constraints and cart data, plus LLM response claim checking.
"""

from typing import Dict, Any, List, Optional
import re
from dataclasses import dataclass, field


@dataclass
class ContradictionResult:
    passed: bool
    violations: List[str] = field(default_factory=list)

    def summary(self) -> str:
        if self.passed:
            return "Grounding check PASSED: No contradictions detected."
        return f"Grounding check BLOCKED ({len(self.violations)} violation(s)): " + "; ".join(self.violations)


def check_response(response_text: str, catalog_truth: List[Dict[str, Any]]) -> ContradictionResult:
    """
    Validates an LLM's conversational text against source-of-truth catalog items.
    Detects commerce hallucinations (e.g. claiming ₹1 for a ₹4,999 item).
    """
    violations = []
    if not response_text or not catalog_truth:
        return ContradictionResult(passed=True, violations=[])

    price_matches = re.findall(r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d+)?)", response_text, re.IGNORECASE)
    mentioned_prices = []
    for p in price_matches:
        try:
            mentioned_prices.append(float(p.replace(",", "")))
        except ValueError:
            pass

    for item in catalog_truth:
        actual_price = float(item.get("price_inr", item.get("price", 0)))
        item_name = str(item.get("name", "")).lower()
        
        name_words = [w for w in item_name.split() if len(w) > 3]
        item_mentioned = any(w in response_text.lower() for w in name_words) if name_words else True
        
        if item_mentioned and mentioned_prices:
            for price in mentioned_prices:
                if price < actual_price * 0.5 or price > actual_price * 1.5:
                    violations.append(
                        f"Price contradiction: Claimed INR {price} for '{item.get('name')}' (actual price: INR {actual_price})"
                    )

    return ContradictionResult(passed=len(violations) == 0, violations=violations)

class ContradictionDetector:
    def __init__(self):
        self.negative_intent_patterns = [
            r"(?:don'?t|do\s+not)\s+want\s+(?:to\s+(?:have|buy|get)\s+)?([a-zA-Z0-9_]+(?:\s+[a-zA-Z0-9_]+){0,3})",
            r"avoid\s+([a-zA-Z0-9_]+(?:\s+[a-zA-Z0-9_]+){0,3})",
            r"exclude\s+([a-zA-Z0-9_]+(?:\s+[a-zA-Z0-9_]+){0,3})"
        ]

        self.spend_limit_patterns = [
            r"(?:not|don'?t)\s+(?:want\s+to\s+)?spend\s+more\s+than\s+(\d+(?:\.\d+)?)",
            r"under\s+(\d+(?:\.\d+)?)",
            r"max\s+(?:of\s+)?(\d+(?:\.\d+)?)",
        ]

        # NEW: patterns that indicate a prompt-injection / instruction-override attempt
        self.injection_patterns = [
            r"ignore\s+(?:the\s+)?(?:previous|prior|above|all)\s+instructions?",
            r"disregard\s+(?:the\s+)?(?:previous|prior|above|all)\s+instructions?",
            r"forget\s+(?:the\s+)?(?:previous|prior|above|all)\s+(?:instructions?|rules?|context)",
            r"you\s+are\s+now\s+(?:a|an)\s+",
            r"system\s*prompt",
            r"new\s+instructions?\s*:",
            r"override\s+(?:the\s+)?(?:previous|prior|system)",
            r"call\s+checkout\s*\(",          # direct function-call injection attempt
            r"\bamount\s*=\s*\d+",             # attacker trying to set amount= directly
            r"act\s+as\s+(?:if|though)",
        ]

    def detect_contradictions(
        self, 
        user_intent_text: str, 
        cart_items: List[Dict[str, Any]], 
        total_spend: Any, 
        max_spend_limit: Any
    ) -> Dict[str, Any]:
        raw_contradictions = []
        
        if not isinstance(user_intent_text, str):
            intent_str = ""
        else:
            intent_str = user_intent_text.lower().strip()

        # NEW: injection check runs first, before anything else
        for pattern in self.injection_patterns:
            if re.search(pattern, intent_str, re.IGNORECASE):
                raw_contradictions.append(
                    f"BLOCKED: Prompt-injection / instruction-override attempt detected in user input (pattern: '{pattern}')."
                )

        try:
            safe_total_spend = max(0.0, float(total_spend or 0.0))
        except (ValueError, TypeError):
            safe_total_spend = 0.0

        # ... rest of your existing code stays exactly the same ...


class ContradictionDetector:
    def __init__(self):
        self.negative_intent_patterns = [
            r"(?:don'?t|do\s+not)\s+want\s+(?:to\s+(?:have|buy|get)\s+)?([a-zA-Z0-9_]+(?:\s+[a-zA-Z0-9_]+){0,3})",
            r"avoid\s+([a-zA-Z0-9_]+(?:\s+[a-zA-Z0-9_]+){0,3})",
            r"exclude\s+([a-zA-Z0-9_]+(?:\s+[a-zA-Z0-9_]+){0,3})"
        ]

        self.spend_limit_patterns = [
            r"(?:not|don'?t)\s+(?:want\s+to\s+)?spend\s+more\s+than\s+(\d+(?:\.\d+)?)",
            r"under\s+(\d+(?:\.\d+)?)",
            r"max\s+(?:of\s+)?(\d+(?:\.\d+)?)",
        ]

    def detect_contradictions(
        self, 
        user_intent_text: str, 
        cart_items: List[Dict[str, Any]], 
        total_spend: Any, 
        max_spend_limit: Any
    ) -> Dict[str, Any]:
        raw_contradictions = []
        
        if not isinstance(user_intent_text, str):
            intent_str = ""
        else:
            intent_str = user_intent_text.lower().strip()

        try:
            safe_total_spend = max(0.0, float(total_spend or 0.0))
        except (ValueError, TypeError):
            safe_total_spend = 0.0

        try:
            safe_max_limit = max(0.0, float(max_spend_limit or 0.0))
        except (ValueError, TypeError):
            safe_max_limit = 0.0

        for pattern in self.spend_limit_patterns:
            match = re.search(pattern, intent_str)
            if match:
                try:
                    stated_limit = float(match.group(1))
                    if safe_total_spend > stated_limit:
                        raw_contradictions.append(
                            f"Contradiction: Intent text restricts spend to {stated_limit}, but actual cart total is {safe_total_spend}."
                        )
                except (ValueError, TypeError):
                    pass

        if safe_max_limit > 0 and safe_total_spend > safe_max_limit:
            raw_contradictions.append(
                f"Contradiction: Cart total ({safe_total_spend}) exceeds authorized max spend limit ({safe_max_limit})."
            )

        _LEADING_FILLERS = {"a", "an", "the", "any", "some"}
        if isinstance(cart_items, list):
            for pattern in self.negative_intent_patterns:
                matches = re.findall(pattern, intent_str)
                for forbidden in matches:
                    forbidden_term = forbidden.strip().lower()
                    if not forbidden_term or len(forbidden_term) < 3:
                        continue
                    words = forbidden_term.split()
                    if words and words[0] in _LEADING_FILLERS:
                        forbidden_term = " ".join(words[1:])
                    if not forbidden_term:
                        continue
                    forbidden_words = [w for w in forbidden_term.split() if len(w) >= 4]
                    if not forbidden_words:
                        forbidden_words = [forbidden_term]

                    for item in cart_items:
                        if not isinstance(item, dict):
                            continue
                        item_name = str(item.get("name", "")).lower()
                        item_id = str(item.get("id", "")).lower()
                        hit = forbidden_term in item_name or forbidden_term in item_id or any(
                            w in item_name or w in item_id for w in forbidden_words
                        )
                        if hit:
                            raw_contradictions.append(
                                f"Contradiction: User requested to avoid/exclude '{forbidden_term}', but item '{item.get('name', item_id)}' is in the cart."
                            )

        contradictions = list(dict.fromkeys(raw_contradictions))
        is_contradictory = len(contradictions) > 0

        return {
            "is_contradictory": is_contradictory,
            "contradiction_count": len(contradictions),
            "contradictions": contradictions
        }


if __name__ == "__main__":
    detector = ContradictionDetector()
    mock_cart = [{"id": "prod_esp32", "name": "ESP32 Dev Board", "price": 499.0}]
    result = detector.detect_contradictions(
        user_intent_text="I want an esp32 but do not want to spend more than 300",
        cart_items=mock_cart,
        total_spend="499.0",
        max_spend_limit=2000.0
    )
    print(result)
    assert result["is_contradictory"] is True

    # Test check_response
    res = check_response("The Soundbar is INR 1 only.", [{"name": "Soundbar", "price": 4999}])
    print("check_response test:", res.summary())
    assert not res.passed
