"""
receipt_chain.py
---------------------------------
Post-checkout evidence trail. Distinct from mandate/chain.py (which
hash-links Intent -> Cart -> Payment mandates BEFORE the transaction
executes). This chain links what actually HAPPENED, in order:
mandate chain result -> checkout result -> grounding check result ->
final receipt. Same SHA-256 hash-linking pattern for consistency.

Framed as "dispute-grade evidence": if a user later disputes a
transaction, this chain is exportable as a single JSON artifact
showing every step was mandate-verified, RBI step-up compliant (or
correctly blocked), and grounded — with tamper-evidence via hashing.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


@dataclass
class Receipt:
    receipt_id: str
    timestamp: float
    mandate_chain_hash: str       # final hash from mandate/chain.py's verified chain
    checkout_order_id: str
    checkout_mode: str            # "live" or "fallback" — see checkout/fallback_mode.py
    amount_inr: float
    grounding_passed: bool
    prev_hash: str
    this_hash: str = field(default="", init=False)

    def _payload_for_hash(self) -> str:
        payload = {
            "receipt_id": self.receipt_id,
            "timestamp": self.timestamp,
            "mandate_chain_hash": self.mandate_chain_hash,
            "checkout_order_id": self.checkout_order_id,
            "checkout_mode": self.checkout_mode,
            "amount_inr": self.amount_inr,
            "grounding_passed": self.grounding_passed,
            "prev_hash": self.prev_hash,
        }
        return json.dumps(payload, sort_keys=True)

    def compute_hash(self) -> str:
        return _sha256(self._payload_for_hash())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ReceiptChain:
    GENESIS_HASH = "0" * 64

    def __init__(self, storage_path: str = "receipt_chain.json"):
        self.storage_path = storage_path
        self._receipts: List[Receipt] = []
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        import os
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.get("receipts", []):
                        r = Receipt(
                            receipt_id=item["receipt_id"],
                            timestamp=item["timestamp"],
                            mandate_chain_hash=item["mandate_chain_hash"],
                            checkout_order_id=item["checkout_order_id"],
                            checkout_mode=item["checkout_mode"],
                            amount_inr=item["amount_inr"],
                            grounding_passed=item["grounding_passed"],
                            prev_hash=item["prev_hash"],
                        )
                        r.this_hash = item["this_hash"]
                        self._receipts.append(r)
            except Exception:
                self._receipts = []

    def _save_to_disk(self) -> None:
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                f.write(self.export_for_dispute())
        except Exception:
            pass

    def add_receipt(
        self,
        receipt_id: str,
        mandate_chain_hash: str,
        checkout_order_id: str,
        checkout_mode: str,
        amount_inr: float,
        grounding_passed: bool,
    ) -> Receipt:
        prev_hash = self._receipts[-1].this_hash if self._receipts else self.GENESIS_HASH

        receipt = Receipt(
            receipt_id=receipt_id,
            timestamp=time.time(),
            mandate_chain_hash=mandate_chain_hash,
            checkout_order_id=checkout_order_id,
            checkout_mode=checkout_mode,
            amount_inr=amount_inr,
            grounding_passed=grounding_passed,
            prev_hash=prev_hash,
        )
        receipt.this_hash = receipt.compute_hash()
        self._receipts.append(receipt)
        self._save_to_disk()
        return receipt

    def get_receipts(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._receipts]

    def verify_chain(self) -> bool:
        """Recomputes every hash and checks the links — tamper detection."""
        expected_prev = self.GENESIS_HASH
        for r in self._receipts:
            if r.prev_hash != expected_prev:
                return False
            if r.compute_hash() != r.this_hash:
                return False  # someone edited a field after the fact
            expected_prev = r.this_hash
        return True

    def latest_hash(self) -> str:
        return self._receipts[-1].this_hash if self._receipts else self.GENESIS_HASH

    def export_for_dispute(self) -> str:
        """Human/machine-readable JSON dump — the artifact you'd hand to a
        dispute-resolution process or an auditor."""
        return json.dumps(
            {
                "chain_valid": self.verify_chain(),
                "receipt_count": len(self._receipts),
                "receipts": [r.to_dict() for r in self._receipts],
            },
            indent=2,
            sort_keys=True,
        )



# ---------------------------------------------------------------------------
# Self-test / demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    chain = ReceiptChain()

    chain.add_receipt(
        receipt_id="rcpt_001",
        mandate_chain_hash="deadbeef" * 8,
        checkout_order_id="order_abc123",
        checkout_mode="live",
        amount_inr=17999,
        grounding_passed=True,
    )
    chain.add_receipt(
        receipt_id="rcpt_002",
        mandate_chain_hash="cafebabe" * 8,
        checkout_order_id="sim_order_xyz789",
        checkout_mode="fallback",
        amount_inr=1999,
        grounding_passed=True,
    )

    print("--- Valid chain ---")
    print(f"verify_chain() = {chain.verify_chain()}")
    assert chain.verify_chain() is True

    print("\n--- Tamper test: mutate a field after the fact ---")
    chain._receipts[0].amount_inr = 1  # simulate tampering
    print(f"verify_chain() after tamper = {chain.verify_chain()}")
    assert chain.verify_chain() is False

    # restore for clean export demo
    chain._receipts[0].amount_inr = 17999
    chain._receipts[0].this_hash = chain._receipts[0].compute_hash()
    # NOTE: this "restore" only works because we recompute — in real use,
    # any post-hoc edit breaks verify_chain() permanently. That's the point.

    print("\n--- Dispute-grade export ---")
    print(chain.export_for_dispute())

    print("\nreceipt_chain self-tests passed (tamper correctly detected).")