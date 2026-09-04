"""
Shared hashing helper for the Mandate Chain. Kept in its own file so
intent_mandate.py, cart_mandate.py, and payment_mandate.py can each
import it without depending on each other.
"""

import hashlib
import json
def create_hashed_receipt(data: str, previous_hash: str) -> str:
    payload = f"{data}{previous_hash}".encode('utf-8')
    return hashlib.sha256(payload).hexdigest()

def compute_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()