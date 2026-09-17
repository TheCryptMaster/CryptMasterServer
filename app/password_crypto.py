"""Password-derived encryption for the user's TOTP seed.

A user's login password is used to encrypt their TOTP seed (so the server
never stores the seed decryptable without the user's password). v1 derived
this key via the same non-cryptographic `generate_secret()` PRNG helper as
everything else. Here we use Argon2id (already a project dependency) as the
actual password-based KDF, with a unique per-user salt, feeding a 32-byte key
into AES-256-GCM.
"""
from __future__ import annotations

import base64
import os

from argon2.low_level import Type, hash_secret_raw
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.crypto import DecryptionError

_SALT_LEN = 16
_NONCE_LEN = 12

# Argon2id parameters (time_cost, memory_cost in KiB, parallelism)
_TIME_COST = 3
_MEMORY_COST = 65536
_PARALLELISM = 4


def _derive_key(password: str, salt: bytes) -> bytes:
    return hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt,
        time_cost=_TIME_COST,
        memory_cost=_MEMORY_COST,
        parallelism=_PARALLELISM,
        hash_len=32,
        type=Type.ID,
    )


def encrypt_with_password(password: str, plaintext: str) -> str:
    salt = os.urandom(_SALT_LEN)
    nonce = os.urandom(_NONCE_LEN)
    key = _derive_key(password, salt)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), b"totp-seed")
    return ":".join(base64.b64encode(part).decode("ascii") for part in (salt, nonce, ciphertext))


def decrypt_with_password(password: str, token: str) -> str:
    try:
        salt_b64, nonce_b64, ciphertext_b64 = token.split(":")
        salt = base64.b64decode(salt_b64)
        nonce = base64.b64decode(nonce_b64)
        ciphertext = base64.b64decode(ciphertext_b64)
    except (ValueError, TypeError) as exc:
        raise DecryptionError("malformed ciphertext token") from exc
    key = _derive_key(password, salt)
    try:
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, b"totp-seed")
    except Exception as exc:  # noqa: BLE001
        raise DecryptionError("bad password") from exc
    return plaintext.decode("utf-8")
