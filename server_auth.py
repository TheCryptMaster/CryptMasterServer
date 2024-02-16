from argon2 import PasswordHasher
from utilities.database_connectivity import query_db
from utilities.secret_generator import generate_secret
from utilities.key_crypt import decrypt_secret, encrypt_secret

class CryptMasterClientAuth:
    def __init__(self):
        self._PENDING_AUTHS = []
        self._AUTH_SEED = generate_secret(None, 64)

    def initiate_auth(self, payload):
        print(payload)
        ip_address, system_id = payload['ip_address'], payload['system_id']
        encrypted_id = generate_secret(str(system_id))
        encrypted_ip = generate_secret(ip_address)
        get_salt = query_db(f"SELECT server_salt FROM app_servers WHERE server_name = '{encrypted_id}' AND ip_address = '{encrypted_ip}'")
        if len(get_salt) == 0:
            return False, None
        server_salt = decrypt_secret(generate_secret('system_salt'), get_salt['server_salt'][0])
        nonce = generate_secret(generate_secret() + self._AUTH_SEED)
        expected_response = nonce + server_salt
        self._PENDING_AUTHS.append(expected_response)
        response = {'response': 'Awaiting Key', 'nonce': nonce}
        return response

    def validate_secret(self, provided_secret):
        if provided_secret == None:
            return False
        ph = PasswordHasher()
        for secret in self._PENDING_AUTHS:
            if ph.verify(provided_secret, secret):
                self._PENDING_AUTHS.delete(secret)
                return True
        return False

