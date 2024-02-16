import os
import random
import sys

from PypeDreams import pype_dreamer
from utilities.seed_tools import generate_seed, get_entropy




entropy_file = '.entropy'


def clear():
    # for windows
    if os.name == 'nt':
        _ = os.system('cls')
    # for mac and linux(here, os.name is 'posix')
    else:
        _ = os.system('clear')


def get_option():
    # For some reason it wont stop on this input, so am moving to its own function
    option = input('There is currently no seed generated for this server.\nIf you have an existing seed, you can restore it now.\n\nPlease pick an option.\n1) Create new seed\n2) Restore from seed phrase\n')
    return option


def check_entropy():
    if os.path.isfile(entropy_file):
        return
    pick_option = get_option()
    if pick_option == '2':
        restore_seed()
        return
    entropy, seed_phrase = generate_seed()
    while True:
        prepare_user = input(
                    '\nYou have chosen to create a new seed.  It is imperative that you protect it as if all of your keys depend on it, BECAUSE THEY DO!!!\n\n'
                    'Hand write down your seed phrase.\n'
                    'DO NOT TAKE A PICTURE OF IT\n'
                    'DO NOT COPY IT TO A TEXT FILE\n'
                    'DO NOT PUT IT IN A PASSWORD MANAGER\n'
                    'DO NOT GIVE IT THAT RANDO THAT SLID IN TO YOUR DMS\n'
                    'IF YOUR SEED IS LOST, NO ONE CAN HELP YOU GET IT BACK\n'
                    '\nDo you understand? ')
        if prepare_user.lower()[:1] == 'y':
            break
    seed_phrase = seed_phrase.split()
    seed_text = "\n\nYou're new seed phrase is:\n\n"
    pass_check = []
    for i, word in enumerate(seed_phrase, start=1):
        seed_text += f'{i}) {word}, '
        pass_check.append([i, word])
    seed_text = seed_text[:-2] + f'\n\nYour Confirmation Phrase is {get_safety_words(entropy)}'
    print(seed_text)
    attempts = 0
    while True:
        if attempts > 2:
            sys.exit()
        ready = input('\n\nWhen you have finished writing down your passphrase, press "C" to continue\n')
        if ready.lower() == 'c':
            attempts += 1
            if test_user(pass_check):
                break
    write_entropy_file(entropy)


def get_safety_words(entropy):
    safety_phrase = pype_dreamer(str(entropy), style='titlecase')
    return safety_phrase


def write_entropy_file(entropy):
    with open(entropy_file, 'w+') as f:
        f.write(str(entropy))


def convert_list_to_passphrase(word_list):
    passhrase = ''
    for word in word_list:
        passhrase += f'{word} '
    return passhrase[:-1]


def restore_seed():
    clear()
    word_list = []
    print('\nRestore your seed phrase\n')
    i = 1
    while len(word_list) < 24:
        word = input(f'Enter word #{i}: ')
        word_list.append(word.lower())
        i += 1
    seed = convert_list_to_passphrase(word_list)
    entropy = get_entropy(seed)
    safety_phrase = get_safety_words(entropy)
    print(f'Your Seed Safety Phrase is {safety_phrase}')
    question = input('\nIs that correct?: ')
    if question.lower()[:1] == 'y':
        write_entropy_file(entropy)






def test_user(seed_phrase):
    clear()
    random_sample = random.sample(seed_phrase, 5)
    for word_item in random_sample:
        position, word = word_item[0], word_item[1]
        count = 0
        while True:
            if count > 2:
                return False
            test = input(f'Enter the seed word in position {position}: ')
            if test.lower() != word.lower():
                count += 1
                print('Please Try Again')
                continue
            break
    return True



def run_seed_manager():
    global ENTROPY
    check_entropy()
    with open(entropy_file, 'r') as f:
        ENTROPY = f.read()


run_seed_manager()