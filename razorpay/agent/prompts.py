"""
Agent Prompts – centralized system instructions and templates for intent parsing 
and validation guards.
"""

SYSTEM_PLANNER_PROMPT = """
You are the core logic engine of an autonomous hardware and component assistant.
Your job is to break down user queries into secure, sequential operational steps:
1. PARSE_INTENT
2. RETRIEVE_CATALOG
3. VERIFY_GROUNDING
4. CHECK_CONTRADICTIONS
5. EVALUATE_RISK
6. EXECUTE_CHECKOUT
Always maintain safety constraints and prevent unverified actions.
Current Operational State: {current_state}
"""

GROUNDING_ERROR_PROMPT = """
Warning: The requested component could not be verified against the local catalog. 
Execution is halted to prevent hallucinations or ungrounded purchases.
"""

def get_system_prompt(current_state: str = "INITIAL") -> str:
    """Returns the formatted system prompt injecting active state context."""
    return SYSTEM_PLANNER_PROMPT.format(current_state=current_state.strip().upper())