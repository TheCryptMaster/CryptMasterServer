from argon2 import PasswordHasher
from utilities.database_connectivity import query_db

class CryptMasterClientAuth:
    def __init__(self):
        some_value = None

    def validate_secret(self, provided_secret):
