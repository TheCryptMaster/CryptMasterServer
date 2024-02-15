import io
import pyotp
import qrcode

# Lots of work left for this script
from getpass import getpass
from password_strength import PasswordPolicy
from utilities.database_connectivity import query_db, execute_db
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
    user_email = input('Please enter the user email address: ')
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
        elif isinstance(user_expiry, int):
            user_expiry = int(user_expiry)
        else:
            print('\nPlease enter a numerical value, or leave blank for default.\n')
            continue
        break
    provisioning_uri, encrypted_otp = generate_user_creds(user_email, user_pass)
    add_user_to_db(user_email, encrypted_otp, user_expiry)
    print('\nUser added!  Use QR Code to Onboard\n')
    display_qr(provisioning_uri)
    return




def add_user_to_db(user_email, encrypted_otp, user_expiry):
    assert check_existing('user', user_email) is None
    execute_db(f"INSERT INTO USER_ACCOUNTS(username, user_otp_hash, active_until) VALUES('{user_email}', '{slqalchemy_escape(encrypted_otp)}', NOW() + '{user_expiry} DAYS')")
    return

def slqalchemy_escape(sql_string):
    fixed_string = sql_string.replace('%', '%%').replace(':', '\:')
    return fixed_string




def generate_user_creds(user_email, user_pass):
    otp = generate_secret()
    provisioning_uri = pyotp.totp.TOTP(otp).provisioning_uri(name=user_email, issuer_name=OTP_ISSUER)
    encrypted_otp = encrypt_secret(user_pass, otp)
    return provisioning_uri, encrypted_otp
