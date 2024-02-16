#!/usr/bin/python3

import io
import os
import pyotp
import qrcode
import sys

# Lots of work left for this script
from datetime import datetime, timezone
from getpass import getpass
from password_strength import PasswordPolicy
from time import sleep
from utilities.database_connectivity import query_db, execute_db, set_domain_name, set_host_name
from utilities.secret_generator import generate_secret
from utilities.key_crypt import encrypt_secret, decrypt_secret





# New users will require both a password, and a one time passcode
# Password will be used to encrypt the OTP seed info
# We will first try to decrypt the users seed with their password, if that fails, then user has sent bad password
# If successful, we decrypt the OTP seed, and verify the user has sent a good OTP.

OTP_ISSUER = 'Crypt Master'


PASS_POLICY = PasswordPolicy.from_names(
    length=8,
    uppercase=1,
    numbers=1,
    special=1,
    nonletters=1
)

PASS_STRENGTH = PasswordPolicy.from_names(entropybits=25)


def clear_screen():
    # for windows
    if os.name == 'nt':
        _ = os.system('cls')
    else:
        _ = os.system('clear')



def display_qr(totp):
    parsed_code = pyotp.parse_uri(totp)
    qr = qrcode.QRCode()
    qr.add_data(parsed_code.provisioning_uri())
    f = io.StringIO()
    qr.print_ascii(out=f)
    f.seek(0)
    print(f.read())
    return



def check_existing(object_type, query_string):
    db_row, lookup = None, []
    if object_type == 'user':
        lookup = query_db(f"SELECT id db_row FROM user_accounts WHERE username = '{query_string}'")
    elif object_type == 'app_server':
        lookup = query_db(f"SELECT id db_row FROM app_servers WHERE server_name = '{query_string}'")
    elif object_type == 'ipv4_allow':
        lookup = query_db(f"SELECT id db_row FROM ipv4_allow WHERE ipv4_address = '{query_string}'")
    elif object_type == 'ipv4_deny':
        lookup = query_db(f"SELECT id db_row FROM ipv4_blacklist WHERE ipv4_address = '{query_string}'")
    if len(lookup) != 0:
        db_row = int(lookup['db_row'][0])
    return db_row



def add_user():
    user_email = input('\nPlease enter the user email address: ')
    if check_existing('user', user_email) is not None:
        print('User already exists in database!')
        return
    password_count = 0
    while True:
        password_count += 1
        if password_count > 3:
            print('\nToo many incorrect passwords.')
            return
        user_pass = getpass('Please enter new user password: ')
        pass_policy, pass_strength = PASS_POLICY.test(user_pass), PASS_STRENGTH.test(user_pass)
        if len(pass_policy) != 0 or len(pass_strength) != 0:
            print('\nPassword does not meet complexity requirements\n')
            continue
        confirm_pass = getpass('Please confirm password: ')
        if user_pass != confirm_pass:
            print('\nPassword and Confirmation do not match!\n')
            continue
        break
    error_count = 0
    while True:
        error_count += 1
        if error_count > 3:
            print('\nFailed to create user!\n')
        user_expiry = input('How long do you want the account active for? (default 365): ')
        if user_expiry == '':
            user_expiry = 365
        try:
            user_expiry = int(user_expiry)
        except:
            print('\nPlease enter a numerical value, or leave blank for default.\n')
            continue
        break
    provisioning_uri, encrypted_otp = generate_user_creds(user_email, generate_secret(user_pass))
    add_user_to_db(user_email, encrypted_otp, user_expiry)
    print('\nUser added!  Use QR Code to Onboard\n')
    display_qr(provisioning_uri)
    sys.exit()



def get_system_users():
    system_users = []
    execute_db(f"UPDATE user_accounts SET is_active = False WHERE now() > active_until AND is_active = True")
    all_users = query_db(f"SELECT id user_row, username, is_active, active_until FROM user_accounts")
    if len(all_users) == 0:
        return system_users
    i = 0
    while i < len(all_users):
        user_row, encrypted_user_name, is_active, active_until = int(all_users['user_row'][i]), all_users['username'][i], bool(all_users['is_active'][i]), all_users['active_until'][i].to_pydatetime()
        user_name = decrypt_secret(generate_secret('username'), encrypted_user_name)
        if not is_active:
            time_remaining = 'EXPIRED/DISABLED'
        else:
            time_remaining = str((active_until - datetime.now(timezone.utc)).days) + ' Day(s)'
        system_users.append([user_row, user_name, time_remaining])
        i += 1
    return system_users


def get_pending_enrollments():
    pending_enrollments = []
    enrollments = query_db(f"SELECT id enrollment_row, pending_enrollment, date_requested FROM pending_enrollments WHERE is_expired = False AND enrollment_complete = False")
    if len(enrollments) == 0:
        return pending_enrollments
    i = 0
    while i < len(enrollments):
        enrollment_row, pending_enrollment, date_requested = int(enrollments['enrollment_row'][i]), enrollments['pending_enrollment'][i], enrollments['date_requested'][i].to_pydatetime()
        decrypted_payload = decrypt_secret(generate_secret('enrollment'), pending_enrollment)
        pending_enrollments.append([enrollment_row, decrypted_payload, date_requested])
        i += 1
    return pending_enrollments

def approve_server(server_details):
    enroll_row, payload = server_details[0], server_details[1]
    system_id, system_salt, ip_address = payload.get('system_id'), payload.get('system_salt'), payload.get('ip_address')
    encrypted_id = generate_secret(str(system_id))
    encrypted_salt = encrypt_secret(generate_secret('system_salt'), system_salt)
    encrypted_ip = generate_secret(ip_address)
    execute_db(f"INSERT INTO app_servers(server_name, ip_address, server_salt) VALUES('{encrypted_id}', '{encrypted_ip}', '{encrypted_salt}')")
    execute_db(f"UPDATE pending_enrollments SET enrollment_complete = True WHERE id = {enroll_row}")
    return


def update_remove_user():
    pass



def add_user_to_db(user_email, encrypted_otp, user_expiry):
    user_email = encrypt_secret(generate_secret('username'), user_email)
    assert check_existing('user', user_email) is None
    execute_db(f"INSERT INTO USER_ACCOUNTS(username, user_otp_hash, active_until) VALUES('{user_email}', '{encrypted_otp}', NOW() + '{user_expiry} DAYS')")
    return


def user_management():
    system_users = get_system_users()
    # ToDo Add splash, and options to udpate users.
    add_user()


def generate_user_creds(user_email, user_pass):
    otp = generate_secret()
    provisioning_uri = pyotp.totp.TOTP(otp).provisioning_uri(name=user_email, issuer_name=OTP_ISSUER)
    encrypted_otp = encrypt_secret(user_pass, otp)
    return provisioning_uri, encrypted_otp


def display_options():
    options = ['User Management', 'Set Host Name', 'Set Domain Name', 'Quit']
    clear_screen()
    display_string = ('\nWelcome to the Crypt Master Setup.  Please choose from the following'
                      ' options.\n\n')
    for i, option in enumerate(options, start=1):
        display_string += f'{i}) {option}\n'
    display_string += '\n'
    selection = input(display_string)
    return selection





def run_setup():
    clear_screen()
    print('\nSetup Script is under development. Not all items work yet.')
    sleep(2)
    fail_count = 0
    while True:
        if fail_count > 2:
            clear_screen()
            print('\nToo many failures.  Please run setup again.')
            sys.exit()
        selection = display_options()
        if selection == '1':
            clear_screen()
            user_management()
        elif selection == '2':
            clear_screen()
            set_host_name()
        elif selection == '3':
            clear_screen()
            set_domain_name()
        elif selection == '4':
            clear_screen()
            print('\nThank you for using the Crypt Master!\n')
            sys.exit()
        else:
            print('\nThat is not a valid option')
            sleep(3)
            fail_count += 1


run_setup()