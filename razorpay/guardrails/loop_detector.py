"""
Recursive Loop Detector – tracks agent thought iterations and tool calls 
using deterministic serialization, consecutive tail-matching, and an efficient deque sliding window.
"""

from typing import Any
from collections import deque
import json

class LoopDetector:
    def __init__(self, max_repeats: int = 5, window_size: int = 20):
        """
        Initializes the loop detector with a consecutive repeat threshold and a fixed-size deque window.
        """
        self.max_repeats = max(1, max_repeats)
        self.window_size = max(self.max_repeats, window_size)
        self.history: deque = deque(maxlen=self.window_size)

    def _serialize_signature(self, signature: Any) -> str:
        """Deterministically serializes action signatures (handles dicts/JSON safely)."""
        if isinstance(signature, (dict, list)):
            try:
                return json.dumps(signature, sort_keys=True, default=str)
            except Exception:
                pass
        return str(signature).strip().lower()

    def check_loop(self, current_action_signature: Any) -> bool:
        """
        Records the action signature and returns True if the exact same action 
        has been executed consecutively back-to-back >= max_repeats times.
        """
        if current_action_signature is None:
            return False

        signature = self._serialize_signature(current_action_signature)
        self.history.append(signature)

        if len(self.history) < self.max_repeats:
            return False

        tail = list(self.history)[-self.max_repeats:]
        is_looping = all(item == signature for item in tail)
        if is_looping:
            self.reset()  # Reset so subsequent legitimate retries are not permanently locked
        return is_looping


    def reset(self):
        """Resets history between independent user sessions or workflows."""
        self.history.clear()


if __name__ == "__main__":
    print("--- Testing Optimized Loop Detector ---")
    detector = LoopDetector(max_repeats=3)
    
    action = {"tool": "query_catalog", "query": "esp32"}
    
    print(f"Attempt 1: {detector.check_loop(action)}") # False
    print(f"Attempt 2: {detector.check_loop(action)}") # False
    print(f"Attempt 3: {detector.check_loop(action)}") # True (Loop detected!)