import random
import uuid


from seed_manager import ENTROPY

def get_db_password():
    system_id = uuid.getnode()
    entropy = ENTROPY + 'cryptmasterdbpass' + str(system_id)
    random.seed(entropy)
    ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    db_pass = ''
    for i in range(32):
        db_pass += (random.choice(ALPHABET))
    return db_pass


