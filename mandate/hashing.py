import hashlib
import json
from typing import Any, Dict

def compute_hash(payload: Dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

def create_hashed_receipt(data: str, previous_hash: str) -> str:
    payload = f"{data}{previous_hash}".encode('utf-8')
    return hashlib.sha256(payload).hexdigest()

