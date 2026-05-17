from __future__ import annotations

import hashlib
import hmac
import re

SHA256_HEX_RE = re.compile(r"^[a-fA-F0-9]{64}$")


def sha256_digest(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_sha256_hex(value: str) -> bool:
    return bool(isinstance(value, str) and SHA256_HEX_RE.fullmatch(value))


def verify_sha256_hex(data: bytes, expected_hex: str) -> bool:
    if not is_sha256_hex(expected_hex):
        return False
    return hmac.compare_digest(sha256_hex(data), expected_hex.lower())
