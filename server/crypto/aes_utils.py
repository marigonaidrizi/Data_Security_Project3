from __future__ import annotations

import os
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

AES_KEY_BYTES = 32
AES_GCM_NONCE_BYTES = 12


@dataclass(frozen=True)
class AesGcmPackage:
    nonce: bytes
    ciphertext: bytes


def generate_aes_key(length: int = AES_KEY_BYTES) -> bytes:
    if length not in (16, 24, 32):
        raise ValueError("AES key length must be 16, 24, or 32 bytes.")
    return os.urandom(length)


def generate_nonce(length: int = AES_GCM_NONCE_BYTES) -> bytes:
    if length != AES_GCM_NONCE_BYTES:
        raise ValueError("AES-GCM nonce must be 12 bytes for this protocol.")
    return os.urandom(length)