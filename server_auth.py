from argon2 import PasswordHasher
from utilities.database_connectivity import query_db
from utilities.secret_generator import generate_secret

class CryptMasterClientAuth:
    def __init__(self):
        self._PENDING_AUTHS = []
        self._AUTH_SEED = generate_secret(None, 64)
    def validate_secret(self, provided_secret):
        pass
