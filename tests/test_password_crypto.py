import pytest

from app.crypto import DecryptionError
from app.password_crypto import decrypt_with_password, encrypt_with_password


def test_round_trip():
    token = encrypt_with_password("correct horse battery staple", "JBSWY3DPEHPK3PXP")
    assert decrypt_with_password("correct horse battery staple", token) == "JBSWY3DPEHPK3PXP"


def test_wrong_password_fails():
    token = encrypt_with_password("correct horse battery staple", "JBSWY3DPEHPK3PXP")
    with pytest.raises(DecryptionError):
        decrypt_with_password("wrong password", token)
