"""
mandate/intent_mandate.py
-------------------------
Intent Mandate — first link in the AP2 chain.
Records user authorization, spend ceiling, and category allowances.
"""

import time
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any

try:
    from mandate.hashing import compute_hash
except ImportError:
    try:
        from .hashing import compute_hash
    except ImportError:
        from hashing import compute_hash


@dataclass
class IntentMandate:
    user_id: str
    max_spend_inr: float
    allowed_categories: List[str]
    created_at: float = field(default_factory=time.time)
    mandate_hash: str = field(default="", init=False)

    def __post_init__(self):
        self.mandate_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        payload = {k: v for k, v in asdict(self).items() if k != "mandate_hash"}
        return compute_hash(payload)

    def verify_integrity(self) -> bool:
        """Recompute hash from CURRENT field values and compare to frozen hash."""
        return self.mandate_hash == self._compute_hash()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


if __name__ == "__main__":
    intent = IntentMandate(user_id="user-priya-01", max_spend_inr=20000, allowed_categories=["subscription"])
    print("Intent hash:", intent.mandate_hash)
    print("Integrity OK:", intent.verify_integrity())
    intent.max_spend_inr = 999999  # tamper
    print("Integrity OK after tampering:", intent.verify_integrity())