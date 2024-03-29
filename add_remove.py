#!/usr/bin/python3


print('THIS IS FOR VERSION 1.0.  IT WILL BE REMOVED IN THE RELEASE CANDIDATE FOR 2.0')

import pyotp
import os
from dotenv import load_dotenv
import qrcode
import io
from time import sleep

load_dotenv()

pyotp_issuer = os.getenv('pyotp_issuer')
authenticate_users_file = '.authenticated_users'
authenticated_servers_file = '.authenticated_servers'




def get_authenticated_users():
    with open(authenticate_users_file) as f:
        authenticated_users = f.read().splitlines()
    return authenticated_users


def write_authenticated_users(authenticated_users):
    f = open(authenticate_users_file, 'w+')
    for authenticated_user in authenticated_users:
        f.write(authenticated_user + "\n")
    f.close()
    return


def get_authenticated_servers():
    with open(authenticated_servers_file) as f:
        authenticated_servers = f.read().splitlines()
    return authenticated_servers


def write_authenticated_servers(authenticated_servers):
    f = open(authenticated_servers_file, 'w+')
    for authenticated_server in authenticated_servers:
        f.write(authenticated_server + "\n")
    f.close()
    return


def generate_user():
    clear()
    user_email = input('Enter the email address of the user you are creating: ').lower()
    pyotp_seed = pyotp.random_base32()
    totp = pyotp.totp.TOTP(pyotp_seed).provisioning_uri(name=user_email, issuer_name=pyotp_issuer)
    authenticated_users = get_authenticated_users()
    if user_email not in authenticated_users:
        authenticated_users.append(user_email)
        authenticated_users.append(pyotp_seed)
        write_authenticated_users(authenticated_users)
        display_qr(totp)
        while True:
            input('\n\nAdd your code to your authenticator app now.  Press Enter to continue.')
            break
        clear()
    else:
        print('\n\nThat user already exists.  Use remove user first to re-create OTP Seed.')
        print('\nReturning to main menu in 5 seconds.')
        sleep(5)
        clear()
    return


def remove_user():
    clear()
    while True:
        i, display_ix = 0, 1
        authenticated_users = get_authenticated_users()
        if len(authenticated_users) == 0:
            print('No users currently authorized.  Use add user to add an authenticated user.')
            print('Returning to main menu in 5 seconds.')
            sleep(5)
            clear()
            return
        display_list = 'Please select the user to remove below\n'
        for user in authenticated_users:
            if i % 2 == 0:
                display_list += f'\n{display_ix}) - {user}'
                display_ix += 1
            i += 1
        display_list += '\nq) Quit/Cancel\n\n'
        selected_user = input(display_list)
        if selected_user.isdigit():
            authenticated_users.pop((int(selected_user) * 2) - 1)
            authenticated_users.pop((int(selected_user) * 2) - 2)
            write_authenticated_users(authenticated_users)
            if len(authenticated_users) == 0:
                break
        elif selected_user.lower() == 'q':
            break
        clear()
        print('That is not a valid option.  Please try again:\n\n')
    clear()
    return


def add_server():
    clear()
    authenticated_servers = get_authenticated_servers()
    server = input('Enter the IP Address of the Server you would like to add: ').lower()
    if server not in authenticated_servers:
        authenticated_servers.append(server)
        write_authenticated_servers(authenticated_servers)
    else:
        print('\n\nThat server already exists.')
        print('\nReturning to main menu in 5 seconds.')
        sleep(5)
    clear()
    return

def remove_server():
    clear()
    while True:
        i = 1
        authenticated_servers = get_authenticated_servers()
        if len(authenticated_servers) == 0:
            print('No servers currently authorized.  Use add server to add an authenticated server.')
            print('Returning to main menu in 5 seconds.')
            sleep(5)
            clear()
            return
        display_list = 'Please select the server to remove below\n'
        for server in authenticated_servers:
            display_list += f'\n{i}) - {server}'
            i += 1
        display_list += '\nq) Quit/Cancel\n\n'
        selected_server = input(display_list)
        if selected_server.isdigit():
            authenticated_servers.pop(int(selected_server) - 1)
            write_authenticated_servers(authenticated_servers)
            if len(authenticated_servers) == 0:
                break
        elif selected_server.lower() == 'q':
            break
        clear()
        print('That is not a valid option.  Please try again:\n\n')
    clear()
    return






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
    clear()
    while True:
        request_type = input(request_text)
        if request_type.lower() == '1':
            generate_user()
            continue
        elif request_type.lower() == '2':
            remove_user()
            continue
        elif request_type.lower() == '3':
            add_server()
            continue
        elif request_type.lower() == '4':
            remove_server()
            continue
        elif request_type.lower() == 'q':
            break
        clear()
        print('That is not a valid option.  Please try again:\n\n')
    clear()
    print('Thank you for using the Crypt Keeper')
    return



def clear():
    # for windows
    if os.name == 'nt':
        _ = os.system('cls')

    # for mac and linux(here, os.name is 'posix')
    else:
        _ = os.system('clear')


get_request_type()