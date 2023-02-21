#!/usr/bin/python3


import pyotp
import os
from dotenv import load_dotenv

load_dotenv()

pyotp_seed = os.getenv(pyotp_seed)
pyotp_issuer = os.getenv(pyotp_issuer)
authenticate_users_file = '.authenticated_users'




def get_authenticated_users():
    with open(authenticate_users_file) as f:
        authenticated_users = f.read().splitlines()
    return authenticated_users


def write_authenticated_users(authenticated_users):
    f = open(authenticate_users_file, 'r')
    for authenticated_user in authenticated_users:
        f.write(authenticated_user + "\n")
    f.close()


def generate_user():
    user_email = input('Enter the email address of the user you are creating: ')
    totp = pyotp.totp.TOTP(pyotp_seed).provisioning_uri(name=user_email, issuer_name=pyotp_issuer)
    authenticated_users = get_authenticated_users()
    authenticated_users.append(user_email)
    write_authenticated_users(authenticated_users)
    print(totp)
    return



generate_user()