import random
import uuid

from datetime import datetime
from seed_manager import ENTROPY



def generate_secret(passphrase=None, length=32):
    if passphrase is None:
        passphrase = str(datetime.now())
    entropy = ENTROPY + passphrase
    random.seed(entropy)
    ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    random_secret = ''
    for i in range(length):
        random_secret += (random.choice(ALPHABET))
    return random_secret



def get_db_secret():
    system_id = uuid.getnode()
    entropy = ENTROPY + 'cryptmasterdbpass' + str(system_id)
    random.seed(entropy)
    ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    db_pass = ''
    for i in range(32):
        db_pass += (random.choice(ALPHABET))
    return db_pass


#def get_db_secret():
#    return generate_secret('CryptMaster')