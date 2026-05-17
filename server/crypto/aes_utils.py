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

def encrypt_bytes(plaintext: bytes, key: bytes, nonce: bytes | None = None) -> AesGcmPackage:
    if nonce is None:
        nonce = generate_nonce()
    if len(nonce) != AES_GCM_NONCE_BYTES:
        raise ValueError("AES-GCM nonce must be 12 bytes.")
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data=None)
    return AesGcmPackage(nonce=nonce, ciphertext=ciphertext)


def decrypt_bytes(ciphertext: bytes, key: bytes, nonce: bytes) -> bytes:
    if len(nonce) != AES_GCM_NONCE_BYTES:
        raise ValueError("AES-GCM nonce must be 12 bytes.")
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, associated_data=None)
    except (InvalidTag, ValueError) as exc:
        raise ValueError("AES-GCM decryption failed.") from exc
