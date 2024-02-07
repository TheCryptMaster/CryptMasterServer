from mnemonic import Mnemonic










def generate_seed():
    mnemo = Mnemonic("english")
    words = mnemo.generate(strength=256)
    seed = mnemo.to_seed(words, passphrase="CryptMaster")
    return seed, words



def get_entropy(words):
    mnemo = Mnemonic("english")
    entropy = mnemo.to_entropy(words, passphrase="CryptMaster")
    return entropy