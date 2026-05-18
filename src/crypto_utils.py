from __future__ import annotations

"""
Optional helpers for encrypting sensitive fields at rest.

If ENCRYPTION_KEY is not set, values are passed through unchanged so that the
rest of the application can continue to function without migration.
"""

import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


_raw_key = os.environ.get("ENCRYPTION_KEY")
_fernet: Optional[Fernet]
if _raw_key:
    # ENCRYPTION_KEY should be a URL-safe base64-encoded 32-byte key suitable
    # for Fernet, e.g. generated via `python -m cryptography.fernet`.
    _fernet = Fernet(_raw_key.encode("utf-8"))
else:
    _fernet = None


def encrypt_value(value: str) -> str:
    """Encrypt a string value using Fernet if configured, otherwise return as-is."""
    if not value:
        return value
    if _fernet is None:
        return value
    token = _fernet.encrypt(value.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_value(value: str) -> str:
    """Decrypt a previously encrypted string. If decryption fails, return the original."""
    if not value:
        return value
    if _fernet is None:
        return value
    try:
        plaintext = _fernet.decrypt(value.encode("utf-8"))
        return plaintext.decode("utf-8")
    except InvalidToken:
        # Value is not encrypted with our key (or corrupted); return as-is so
        # existing plaintext rows remain usable.
        return value

