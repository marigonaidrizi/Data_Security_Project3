from __future__ import annotations

import hashlib
from typing import Union

from cryptography.exceptions import InvalidKey
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

RSAPrivateKey = rsa.RSAPrivateKey
RSAPublicKey = rsa.RSAPublicKey
PublicKeyInput = Union[str, bytes, RSAPublicKey]


def generate_private_key(key_size: int = 3072) -> RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=key_size)


def public_key_from_private(private_key: RSAPrivateKey) -> RSAPublicKey:
    return private_key.public_key()


def serialize_public_key(public_key: RSAPublicKey) -> str:
    data = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return data.decode("utf-8")


def serialize_private_key(private_key: RSAPrivateKey) -> str:
    data = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return data.decode("utf-8")


def load_public_key(public_key_pem: PublicKeyInput) -> RSAPublicKey:
    if isinstance(public_key_pem, rsa.RSAPublicKey):
        return public_key_pem
    if isinstance(public_key_pem, str):
        public_key_pem = public_key_pem.encode("utf-8")
    try:
        key = serialization.load_pem_public_key(public_key_pem)
    except (ValueError, TypeError) as exc:
        raise ValueError("Invalid public key.") from exc
    if not isinstance(key, rsa.RSAPublicKey):
        raise ValueError("Public key must be an RSA key.")
    return key


def public_key_fingerprint(public_key: PublicKeyInput) -> str:
    key = load_public_key(public_key)
    der = key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return hashlib.sha256(der).hexdigest()


def public_key_size(public_key: PublicKeyInput) -> int:
    return load_public_key(public_key).key_size


def encrypt_with_public_key(public_key: PublicKeyInput, plaintext: bytes) -> bytes:
    key = load_public_key(public_key)
    return key.encrypt(
        plaintext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )


def decrypt_with_private_key(private_key: RSAPrivateKey, ciphertext: bytes) -> bytes:
    try:
        return private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
    except (ValueError, InvalidKey) as exc:
        raise ValueError("RSA-OAEP decryption failed.") from exc
