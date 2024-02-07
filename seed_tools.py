from mnemonic import Mnemonic










def generate_seed():
    mnemo = Mnemonic("english")
    seed_phrase = mnemo.generate(strength=256)
    byte_val = mnemo.to_seed(seed_phrase, passphrase="CryptMaster")
    entropy = int.from_bytes(byte_val, "big")
    return entropy, seed_phrase



def get_entropy(seed_phrase):
    mnemo = Mnemonic("english")
    byte_val = mnemo.to_seed(seed_phrase, passphrase="CryptMaster")
    entropy = int.from_bytes(byte_val, "big")
    return entropy