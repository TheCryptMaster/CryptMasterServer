"""Re-implementation of the v1 encryption scheme, for read-only use by the
migration tool ONLY. Do not use this for anything new -- it exists purely to
decrypt v1 data so migrate_v1_to_v2.py can re-encrypt it under app.crypto.

This is a faithful copy of v1's utilities/secret_generator.py and
utilities/key_crypt.py logic: `generate_secret()` seeds Python's `random`
module (not cryptographically secure) with `entropy_file_contents + passphrase`
and reads characters off a fixed alphabet to produce the AES/PBKDF2 password.
"""
from __future__ import annotations

import base64
import json
import random

from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Util.Padding import unpad

_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def legacy_generate_secret(entropy: str, passphrase: str, length: int = 32) -> str:
    random.seed(entropy + passphrase)
    return "".join(random.choice(_ALPHABET) for _ in range(length))


def _b64d(value: str) -> bytes:
    return base64.decodebytes(value.encode("ascii"))


def legacy_decrypt_secret(decrypt_password: str, encoded_skey: str) -> str:
    salt_b64, iv_b64, ciphertext_b64 = encoded_skey.split(":")
    salt = _b64d(salt_b64)
    iv = _b64d(iv_b64)
    ciphertext = _b64d(ciphertext_b64)
    key = PBKDF2(decrypt_password.encode("ascii"), salt, 32, count=15000, hmac_hash_module=SHA256)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)
    return json.loads(plaintext.decode("utf-8"))
