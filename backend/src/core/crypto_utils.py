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
    _fernet = Fernet(_raw_key.encode("utf-8"))
else:
    _fernet = None


def encrypt_value(value: str) -> str:
    if not value:
        return value
    if _fernet is None:
        return value
    token = _fernet.encrypt(value.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_value(value: str) -> str:
    if not value:
        return value
    if _fernet is None:
        return value
    try:
        plaintext = _fernet.decrypt(value.encode("utf-8"))
        return plaintext.decode("utf-8")
    except InvalidToken:
        return value
