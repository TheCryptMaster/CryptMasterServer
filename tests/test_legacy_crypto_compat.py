"""Confirms the migration tool's legacy re-implementation actually matches
v1's real output, using the exact algorithm from v1's
utilities/secret_generator.py + utilities/key_crypt.py."""
import base64
import json
import random

from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad

from migration.legacy_crypto import legacy_decrypt_secret, legacy_generate_secret

_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _v1_generate_secret(entropy: str, passphrase: str, length: int = 32) -> str:
    random.seed(entropy + passphrase)
    return "".join(random.choice(_ALPHABET) for _ in range(length))


def _v1_encrypt_secret(password: str, plaintext_secret) -> str:
    plaintext = json.dumps(plaintext_secret)
    salt = get_random_bytes(32)
    key = PBKDF2(password.encode("ascii"), salt, 32, count=15000, hmac_hash_module=SHA256)
    cipher = AES.new(key, AES.MODE_CBC)
    ciphertext = cipher.encrypt(pad(plaintext.encode("ascii"), AES.block_size))
    b64 = lambda b: base64.b64encode(b).decode("utf-8")
    return f"{b64(salt)}:{b64(cipher.iv)}:{b64(ciphertext)}"


def test_legacy_generate_secret_matches_v1_algorithm():
    entropy = "some entropy phrase"
    assert legacy_generate_secret(entropy, "domain") == _v1_generate_secret(entropy, "domain")


def test_legacy_decrypt_matches_v1_encrypt():
    entropy = "some entropy phrase"
    password = legacy_generate_secret(entropy, "domain")
    token = _v1_encrypt_secret(password, "example.com")
    assert legacy_decrypt_secret(password, token) == "example.com"
