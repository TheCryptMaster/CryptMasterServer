#!/usr/bin/python3

from utilities.secret_generator import generate_secret


def quick_secret_checker():
    intial_value = str(input('Enter a value to convert: '))
    secret_value = generate_secret(intial_value)
    print(secret_value)



quick_secret_checker()