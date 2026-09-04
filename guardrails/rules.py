"""
Guardrail Rules Layer – enforces hardcoded spend limits, 
category restrictions, and the RBI 2026 step-up threshold (₹15,000 AFA limit).
"""

from typing import List, Dict, Any, Union

# Hardcoded global guardrail policies
MAX_GLOBAL_SPEND_LIMIT = 50000.0  # Absolute hard ceiling for autonomous agent purchases
RBI_STEP_UP_THRESHOLD = 15000.0   # RBI 2026 AFA mandate threshold
BLOCKED_CATEGORIES = {"adult", "gambling", "weapons", "restricted_chemicals"}

def evaluate_guardrails(
    intent_max_spend: float, 
    cart_amount: float, 
    product_category: str, 
    allowed_categories: Union[List[str], str]
) -> Dict[str, Any]:
    """
    Evaluates cart and intent against hardcoded security and regulatory rules.
    Returns a dictionary indicating approval status, step-up requirements, and violation reasons.
    """
    violations = []
    requires_step_up = False

    # Safe type handling and casting
    try:
        max_spend = float(intent_max_spend)
        amount = float(cart_amount)
    except (ValueError, TypeError):
        return {
            "approved": False,
            "requires_step_up": False,
            "violations": ["Invalid financial amount type provided."]
        }

    # Negative value checks
    if amount < 0:
        violations.append("Invalid cart amount: Amount cannot be negative.")
    if max_spend < 0:
        violations.append("Invalid intent max spend: Intent limit cannot be negative.")

    category = (product_category or "").strip().lower()

    # Robust handling if allowed_categories is accidentally passed as a string instead of a list
    if isinstance(allowed_categories, str):
        allowed = [allowed_categories.strip().lower()]
    elif isinstance(allowed_categories, (list, tuple, set)):
        allowed = [str(cat).strip().lower() for cat in allowed_categories if cat]
    else:
        allowed = []

    # 1. Category Blocklist Check
    if category in BLOCKED_CATEGORIES:
        violations.append(f"Blocked category violation: '{product_category}' is strictly prohibited.")

    # 2. User Intent Allowed Categories Check
    if category not in allowed:
        violations.append(f"Category mismatch: '{product_category}' is not within user's allowed categories.")

    # 3. Spend Ceiling Check (Intent vs Cart)
    if amount > max_spend:
        violations.append(f"Spend limit exceeded: Cart amount ({amount}) crosses intent max spend ({max_spend}).")

    # 4. Global Absolute Spend Limit Check
    if amount > MAX_GLOBAL_SPEND_LIMIT:
        violations.append(f"Global safety limit breached: Amount ({amount}) crosses absolute ceiling ({MAX_GLOBAL_SPEND_LIMIT}).")

    # 5. RBI 2026 Step-Up Threshold Check (AFA limit)
    if amount > RBI_STEP_UP_THRESHOLD:
        requires_step_up = True

    is_approved = (len(violations) == 0) and (not requires_step_up)

    return {
        "approved": is_approved,
        "requires_step_up": requires_step_up,
        "violations": violations
    }

if __name__ == "__main__":
    # Test cases to verify rule enforcement
    print("--- Testing Guardrail Rules ---")
    
    # Test 1: Normal valid cart
    res1 = evaluate_guardrails(intent_max_spend=20000, cart_amount=499, product_category="subscription", allowed_categories=["subscription"])
    print(f"Test 1 (Valid Subscription): {res1}")

    # Test 2: Crossing RBI Step-Up Threshold (₹15,000)
    res2 = evaluate_guardrails(intent_max_spend=20000, cart_amount=17999, product_category="subscription", allowed_categories=["subscription"])
    print(f"Test 2 (Step-Up Triggered): {res2}")

    # Test 3: Unauthorized Category / Spend Breach
    res3 = evaluate_guardrails(intent_max_spend=10000, cart_amount=12000, product_category="gambling", allowed_categories=["subscription"])
    print(f"Test 3 (Violations Caught): {res3}")