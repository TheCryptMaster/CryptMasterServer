import random

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