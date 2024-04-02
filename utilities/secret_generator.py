import random

from datetime import datetime
from seed_manager import ENTROPY
from utilities.system_data import get_system_id


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
    #system_id = get_system_id()
    system_id = 'Crypt_keeper'
    entropy = ENTROPY + 'cryptmasterdbpass' + str(system_id)
    random.seed(entropy)
    ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    db_pass = ''
    for i in range(32):
        db_pass += (random.choice(ALPHABET))
    return db_pass

