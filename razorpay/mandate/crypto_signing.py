"""
mandate/crypto_signing.py
-------------------------
Asymmetric Ed25519 Cryptographic Signatures for W3C / AP2 Verifiable Credentials.
Enables non-repudiation: user signs with private key, Razorpay / Bank verifies with public key.
"""

from __future__ import annotations
import base64
import os
from typing import Tuple, Dict, Any
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization


class MandateSigner:
    """Manages user Ed25519 private key for signing verifiable mandates."""
    def __init__(self, key_path: str | None = None):
        if key_path and os.path.exists(key_path):
            with open(key_path, "rb") as f:
                self.private_key = serialization.load_pem_private_key(f.read(), password=None)
        else:
            self.private_key = ed25519.Ed25519PrivateKey.generate()

    def get_public_key_hex(self) -> str:
        public_bytes = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        return public_bytes.hex()

    def sign_hash(self, mandate_hash: str) -> str:
        """Signs a mandate hash and returns hex-encoded digital signature."""
        data = mandate_hash.encode("utf-8")
        signature = self.private_key.sign(data)
        return signature.hex()


def verify_mandate_signature(mandate_hash: str, signature_hex: str, public_key_hex: str) -> bool:
    """Verifies that the mandate hash was signed by the holder of the corresponding public key."""
    try:
        public_bytes = bytes.fromhex(public_key_hex)
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_bytes)
        signature = bytes.fromhex(signature_hex)
        public_key.verify(signature, mandate_hash.encode("utf-8"))
        return True
    except Exception:
        return False


if __name__ == "__main__":
    signer = MandateSigner()
    sample_hash = "ada4501fb6e6490b21921b79679393c9c8ed7e467c40387a61ef7213f7f2375c"
    sig = signer.sign_hash(sample_hash)
    pub = signer.get_public_key_hex()

    print("Public Key:", pub)
    print("Signature:", sig[:32], "...")
    assert verify_mandate_signature(sample_hash, sig, pub) is True
    assert verify_mandate_signature("tampered_hash", sig, pub) is False
    print("Ed25519 AP2 verification self-test passed!")
