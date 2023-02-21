#!/usr/bin/python3


import pyotp
import os
from dotenv import load_dotenv
import qrcode
import io

load_dotenv()

pyotp_seed = os.getenv('pyotp_seed')
pyotp_issuer = os.getenv('pyotp_issuer')
authenticate_users_file = '.authenticated_users'




def get_authenticated_users():
    with open(authenticate_users_file) as f:
        authenticated_users = f.read().splitlines()
    return authenticated_users


def write_authenticated_users(authenticated_users):
    f = open(authenticate_users_file, 'w+')
    for authenticated_user in authenticated_users:
        f.write(authenticated_user + "\n")
    f.close()


def generate_user():
    user_email = input('Enter the email address of the user you are creating: ').lower()
    totp = pyotp.totp.TOTP(pyotp_seed).provisioning_uri(name=user_email, issuer_name=pyotp_issuer)
    authenticated_users = get_authenticated_users()
    if user_email not in authenticated_users:
        authenticated_users.append(user_email)
        write_authenticated_users(authenticated_users)
    display_qr(totp)
    return


def remove_user():
    pass


def add_server():
    pass

def remove_server():
    pass


def display_qr(totp):
    parsed_code = pyotp.parse_uri(totp)
    qr = qrcode.QRCode()
    qr.add_data(parsed_code.provisioning_uri())
    f = io.StringIO()
    qr.print_ascii(out=f)
    f.seek(0)
    print(f.read())
    return



def get_request_type():
    request_text = 'Welcome to the Crypt Keeper\n\nWhich action would you like to perform?:\n\n' \
                   '1) Add Authenticated User\n2) Remove Authenticated User\n' \
                    '3) Add Allowed Server\n4) Remove Allowed Server\nq) Quit\n\n'
    os.system('cls')
    while True:
        request_type = input(request_text)
        if request_type.lower() == '1':
            generate_user()
        elif request_type.lower() == '2':
            remove_user()
        elif request_type.lower() == '3':
            add_server()
        elif request_type.lower() == '4':
            remove_server()
        elif request_type.lower() == 'q':
            break
        os.system('cls')
        print('That is not a valid option.  Please try again:\n\n')


get_request_type()