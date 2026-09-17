import os

import pytest

from app.crypto import DecryptionError, blind_index, decrypt_field, encrypt_field


@pytest.fixture
def master_key() -> bytes:
    return os.urandom(32)


def test_round_trip(master_key):
    token = encrypt_field(master_key, "secret_value", "hunter2")
    assert decrypt_field(master_key, "secret_value", token) == "hunter2"


def test_same_plaintext_different_ciphertext(master_key):
    a = encrypt_field(master_key, "secret_value", "hunter2")
    b = encrypt_field(master_key, "secret_value", "hunter2")
    assert a != b, "each encryption must use a fresh salt/nonce"


def test_wrong_context_fails(master_key):
    token = encrypt_field(master_key, "secret_value", "hunter2")
    with pytest.raises(DecryptionError):
        decrypt_field(master_key, "username", token)


def test_wrong_key_fails(master_key):
    token = encrypt_field(master_key, "secret_value", "hunter2")
    with pytest.raises(DecryptionError):
        decrypt_field(os.urandom(32), "secret_value", token)


def test_tampered_ciphertext_fails(master_key):
    token = encrypt_field(master_key, "secret_value", "hunter2")
    salt_b64, nonce_b64, ct_b64 = token.split(":")
    tampered = f"{salt_b64}:{nonce_b64}:{ct_b64[:-4]}AAAA"
    with pytest.raises(DecryptionError):
        decrypt_field(master_key, "secret_value", tampered)


def test_blind_index_deterministic(master_key):
    assert blind_index(master_key, "username", "a@b.com") == blind_index(master_key, "username", "a@b.com")


def test_blind_index_distinguishes_context(master_key):
    assert blind_index(master_key, "username", "x") != blind_index(master_key, "system_id", "x")
