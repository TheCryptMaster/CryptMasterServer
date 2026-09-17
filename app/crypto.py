"""Authenticated field-level encryption.

Replaces v1's `generate_secret()`, which seeded Python's non-cryptographic
`random` module and reused the *same derived key* for every row of a given
field type (every username was encrypted under one key, every hostname under
another, etc).

Design here:
  * A single high-entropy master key lives outside the database (env var).
  * Every encrypted value gets its own random 16-byte salt.
  * HKDF-SHA256 derives a unique per-value subkey from (master_key, salt, context).
  * AES-256-GCM (authenticated) encrypts the value, with `context` bound in as
    associated data so a ciphertext can't be silently moved to a different
    column/purpose.

Token format (all base64, colon-separated): salt:nonce:ciphertext
"""
from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

_SALT_LEN = 16
_NONCE_LEN = 12


class DecryptionError(Exception):
    """Raised when a token fails authentication or is malformed."""


def _derive_key(master_key: bytes, salt: bytes, context: str) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=context.encode("utf-8"),
    ).derive(master_key)


def encrypt_field(master_key: bytes, context: str, plaintext: str) -> str:
    salt = os.urandom(_SALT_LEN)
    nonce = os.urandom(_NONCE_LEN)
    key = _derive_key(master_key, salt, context)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), context.encode("utf-8"))
    return ":".join(
        base64.b64encode(part).decode("ascii") for part in (salt, nonce, ciphertext)
    )


def decrypt_field(master_key: bytes, context: str, token: str) -> str:
    try:
        salt_b64, nonce_b64, ciphertext_b64 = token.split(":")
        salt = base64.b64decode(salt_b64)
        nonce = base64.b64decode(nonce_b64)
        ciphertext = base64.b64decode(ciphertext_b64)
    except (ValueError, TypeError) as exc:
        raise DecryptionError("malformed ciphertext token") from exc
    key = _derive_key(master_key, salt, context)
    try:
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, context.encode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - cryptography raises a bare InvalidTag
        raise DecryptionError("decryption failed (wrong key or tampered data)") from exc
    return plaintext.decode("utf-8")


def blind_index(master_key: bytes, context: str, value: str) -> str:
    """Deterministic-but-keyed lookup token, so we can `WHERE column = :idx`
    against encrypted columns without ever storing plaintext or falling back
    to string-formatted SQL. Not reversible; used purely as an index."""
    key = _derive_key(master_key, context.encode("utf-8")[:16].ljust(16, b"\0"), f"blind-index:{context}")
    digest = hashes.Hash(hashes.SHA256())
    digest.update(key)
    digest.update(value.encode("utf-8"))
    return base64.urlsafe_b64encode(digest.finalize()).decode("ascii")
