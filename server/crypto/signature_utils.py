from __future__ import annotations

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

PSS_SALT_LENGTH = 32


def sign_hash(private_key: rsa.RSAPrivateKey, file_hash: bytes) -> bytes:
    """Sign the SHA-256 digest bytes as the message for Web Crypto compatibility."""
    return private_key.sign(
        file_hash,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=PSS_SALT_LENGTH,
        ),
        hashes.SHA256(),
    )


def verify_signature(public_key: rsa.RSAPublicKey, signature: bytes, file_hash: bytes) -> bool:
    try:
        public_key.verify(
            signature,
            file_hash,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=PSS_SALT_LENGTH,
            ),
            hashes.SHA256(),
        )
        return True
    except InvalidSignature:
        return False
