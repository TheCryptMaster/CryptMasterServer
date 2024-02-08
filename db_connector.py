import random


from seed_manager import ENTROPY

def get_db_password():
    entropy = ENTROPY + 'cryptmasterdbpass'
    random.seed(entropy)
    ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    db_pass = ''
    for i in range(32):
        db_pass += (random.choice(ALPHABET))
    return db_pass


