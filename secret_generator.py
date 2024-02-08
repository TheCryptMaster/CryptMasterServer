import random

from datetime import datetime
from seed_manager import ENTROPY



def generate_random_secret(length=32):
    entropy = ENTROPY + str(datetime.now())
    random.seed(entropy)
    ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    random_secret = ''
    for i in range(length):
        random_secret += (random.choice(ALPHABET))
    return random_secret